from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import shutil
import threading
import asyncio
import duckdb
import json
from typing import Any
import uuid
import subprocess
import json as _json
from whatsapp_service import whatsapp_service

# Load environment variables from .env file
from dotenv import load_dotenv
BASE_DIR = os.path.dirname(__file__)
SECRETS_DIR = os.path.join(BASE_DIR, "secrets")
os.makedirs(SECRETS_DIR, exist_ok=True)
ENV_PATH = os.path.join(SECRETS_DIR, '.env')
load_dotenv(ENV_PATH)

FRONTEND_DIST = os.path.join(os.path.dirname(BASE_DIR), "dist")

# Import user's pipeline
try:
    from top_news_pipeline import NewsPipeline
    PIPELINE_AVAILABLE = True
except Exception as e:
    print(f"[warn] Could not import NewsPipeline: {e}")
    NewsPipeline = None
    PIPELINE_AVAILABLE = False

# Allow overriding OpenAI API key via environment variable
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

def resolve_secret_path(env_var: str, default_name: str) -> str:
    val = os.getenv(env_var)
    if not val:
        return os.path.join(SECRETS_DIR, default_name)
    if os.path.isabs(val):
        return val
    return os.path.join(SECRETS_DIR, val)

def resolve_db_path():
    val = os.getenv("DUCKDB_PATH")
    if not val:
        return os.path.join(BASE_DIR, "top_news.duckdb")
    if os.path.isabs(val):
        return val
    return os.path.join(BASE_DIR, val)

app = FastAPI()

# Add CORS middleware to allow requests from frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    # Auto-start WhatsApp if enabled
    if os.getenv("WHATSAPP_ENABLED", "false").lower() == "true":
        print("[info] Auto-starting WhatsApp service...")
        whatsapp_service.start()

# Serve static frontend if built
if os.path.isdir(FRONTEND_DIST):
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")

# Shared pipeline instance (lazy)
_pipeline = None
_pipeline_lock = threading.Lock()
_last_run = {"running": False, "last_result": None}


def get_pipeline():
    global _pipeline
    with _pipeline_lock:
        if _pipeline is None and PIPELINE_AVAILABLE:
            _pipeline = NewsPipeline()
        return _pipeline


class RunRequest(BaseModel):
    newsletters: list = []
    fetch_limit: int | None = None


@app.get('/api/status')
async def status():
    return {
        "ok": True,
        "pipeline_available": PIPELINE_AVAILABLE,
        "last_run": _last_run,
    }


@app.post('/api/upload-google-credentials')
async def upload_google_credentials(file: UploadFile = File(...)):
    dest = os.path.join(SECRETS_DIR, 'Google_credentials.json')
    with open(dest, 'wb') as f:
        shutil.copyfileobj(file.file, f)
    return {"ok": True, "path": dest}


@app.post('/api/upload-google-token')
async def upload_google_token(file: UploadFile = File(...)):
    dest = os.path.join(SECRETS_DIR, 'token.json')
    with open(dest, 'wb') as f:
        shutil.copyfileobj(file.file, f)
    return {"ok": True, "path": dest}


@app.post('/api/upload-env')
async def upload_env(file: UploadFile = File(...)):
    dest = os.path.join(SECRETS_DIR, '.env')
    with open(dest, 'wb') as f:
        shutil.copyfileobj(file.file, f)
    return {"ok": True, "path": dest}


@app.post('/api/delete-credentials')
async def delete_credentials():
    """Delete stored Google credentials and token from backend/secrets."""
    removed = []
    errors = []
    targets = [
        'Google_credentials.json', 
        'token.json', 
        '.env', 
        'authority_scores.json', 
        'model_processes.json'
    ]
    for t in targets:
        p = os.path.join(SECRETS_DIR, t)
        try:
            if os.path.exists(p):
                os.remove(p)
                removed.append(t)
        except Exception as e:
            errors.append({"file": t, "error": str(e)})
    return {"ok": True, "removed": removed, "errors": errors}


@app.get('/api/config')
async def get_config():
    """Read current configuration from .env file."""
    env_path = os.path.join(SECRETS_DIR, '.env')
    config = {
        "FETCH_LIMIT": os.getenv("FETCH_LIMIT", "10"),
        "TOP_N": os.getenv("TOP_N", "10"),
        "SIMILARITY_THRESHOLD": os.getenv("SIMILARITY_THRESHOLD", "0.85"),
        "OPENAI_MODEL": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    }
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    k, v = line.strip().split('=', 1)
                    config[k] = v.split('#')[0].strip()
    return {"ok": True, "config": config}


@app.post('/api/config')
async def post_config(payload: dict):
    """Update .env file with new configuration."""
    env_path = os.path.join(SECRETS_DIR, '.env')
    existing = {}
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    k, v = line.strip().split('=', 1)
                    existing[k] = v
    
    # Update with new values
    for k, v in payload.items():
        existing[k] = str(v)
    
    with open(env_path, 'w') as f:
        for k, v in existing.items():
            f.write(f"{k}={v}\n")
    
    # Reload environment variables for the current process
    from dotenv import load_dotenv
    load_dotenv(env_path, override=True)
    
    return {"ok": True}


@app.get('/api/secrets/status')
async def secrets_status():
    """Return which secret files exist in backend/secrets and whether the DuckDB exists."""
    targets = {
        'google_credentials': resolve_secret_path("GOOGLE_CREDENTIALS", "Google_credentials.json"),
        'google_token': resolve_secret_path("GOOGLE_TOKEN", "token.json"),
        'env': os.path.join(SECRETS_DIR, '.env'),
        'duckdb': resolve_db_path(),
        'authority_scores': resolve_secret_path("AUTHORITY_SCORES_PATH", "authority_scores.json"),
        'model_processes': resolve_secret_path("MODEL_PROCESSES_PATH", "model_processes.json")
    }
    out = {}
    for k, p in targets.items():
        out[k] = {
            'exists': os.path.exists(p),
            'path': p
        }
    return {"ok": True, "secrets": out}


def run_cmd(cmd: list, timeout: int = 600):
    """Run a command and return (ok, stdout, stderr, returncode)"""
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)
        return True, proc.stdout, proc.stderr, proc.returncode
    except Exception as e:
        return False, '', str(e), 1


@app.get('/api/openai/status')
async def openai_status():
    # Check if OpenAI API key is configured
    api_key = os.getenv('OPENAI_API_KEY')
    api_available = bool(api_key)
    
    # Check if we can reach OpenAI API
    server_up = False
    running = False
    try:
        import requests
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        r = requests.get("https://api.openai.com/v1/models", headers=headers, timeout=5)
        server_up = r.status_code == 200
        running = server_up  # If API is accessible, we're "running"
    except Exception:
        server_up = False
        running = False
    
    return {
        "ok": True, 
        "cli_available": api_available,  # API key configured
        "server_up": server_up,  # Can reach OpenAI API
        "running": running,  # Ready to use
        "running_models": [os.getenv("OPENAI_MODEL", "gpt-4o-mini")] if running else []
    }
    
# Keep legacy /api/ollama/status for backward compatibility
@app.get('/api/ollama/status')
async def ollama_status():
    return await openai_status()


@app.get('/api/models')
async def list_models():
    # OpenAI models - return the configured model and some common alternatives
    api_key = os.getenv('OPENAI_API_KEY')
    configured_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    
    available_models = [
        {"name": "gpt-4o", "size": "Large (Latest)"},
        {"name": "gpt-4o-mini", "size": "Small (Fast)"},
        {"name": "gpt-4-turbo", "size": "Large (Turbo)"},
        {"name": "gpt-3.5-turbo", "size": "Small (Legacy)"},
    ]
    
    # Mark the configured one as "active"
    for m in available_models:
        if m["name"] == configured_model:
            m["active"] = True
    
    return {"ok": True, "models": available_models, "configured": configured_model, "api_key_set": bool(api_key)}


@app.post('/api/models/pull')
async def pull_model(payload: dict):
    model = payload.get('model')
    if not model:
        return {"ok": False, "error": "no model specified"}
    # OpenAI models don't need to be "pulled" - they're already available via API
    return {"ok": True, "message": f"Model {model} is available via OpenAI API"}


@app.post('/api/models/remove')
async def remove_model(payload: dict):
    model = payload.get('model')
    if not model:
        return {"ok": False, "error": "no model specified"}
    # OpenAI models can't be removed - they live on OpenAI's servers
    return {"ok": False, "error": "Cannot remove OpenAI API models. Configured via OPENAI_MODEL env variable."}


@app.post('/api/models/activate')
async def activate_model(payload: dict):
    global OPENAI_MODEL
    model = payload.get('model')
    if not model:
        return {"ok": False, "error": "no model specified"}
    
    # For OpenAI, "activating" means setting it as the configured model
    env_path = os.path.join(SECRETS_DIR, '.env')
    existing = {}
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    k, v = line.strip().split('=', 1)
                    existing[k] = v
    
    existing['OPENAI_MODEL'] = model
    
    with open(env_path, 'w') as f:
        for k, v in existing.items():
            f.write(f"{k}={v}\n")
    
    # Reload environment variables for the current process
    from dotenv import load_dotenv
    load_dotenv(env_path, override=True)
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    
    return {"ok": True, "message": f"Model {model} is now configured"}


@app.post('/api/models/deactivate')
async def deactivate_model(payload: dict):
    model = payload.get('model')
    if not model:
        return {"ok": False, "error": "no model specified"}
    
    # OpenAI models can't be deactivated - we always need a model configured
    return {"ok": False, "error": "Cannot deactivate OpenAI models. A model must always be configured."}
    return {"ok": False, "error": err or "Failed to stop model"}


@app.get('/api/newsletters')
async def get_newsletters():
    db_path = resolve_db_path()
    if not os.path.exists(db_path):
        return {"ok": True, "newsletters": []}
    con = duckdb.connect(db_path)
    try:
        # newsletter_addresses table: id, sender, email, priority
        try:
            rows = con.execute('SELECT id, sender, email, priority FROM newsletter_addresses ORDER BY sender').fetchall()
            cols = [c[0] for c in con.description]
            nl = [dict(zip(cols, r)) for r in rows]
            return {"ok": True, "newsletters": nl}
        except Exception:
            return {"ok": True, "newsletters": []}
    finally:
        con.close()


@app.post('/api/newsletters')
async def post_newsletters(payload: dict):
    items = payload.get('newsletters', [])
    db_path = resolve_db_path()
    con = duckdb.connect(db_path)
    try:
        con.execute('CREATE TABLE IF NOT EXISTS newsletter_addresses (id TEXT PRIMARY KEY, sender TEXT, email TEXT, priority INTEGER)')
        # replace contents
        con.execute('DELETE FROM newsletter_addresses')
        for it in items:
            _id = it.get('id') or str(uuid.uuid4())
            sender = it.get('sender') or ''
            email = it.get('email') or ''
            priority = int(it.get('priority') or 5)
            con.execute('INSERT INTO newsletter_addresses (id, sender, email, priority) VALUES (?, ?, ?, ?)', (_id, sender, email, priority))
        return {"ok": True, "count": len(items)}
    finally:
        con.close()


@app.get('/api/priority-keywords')
async def get_priority_keywords():
    db_path = resolve_db_path()
    if not os.path.exists(db_path):
        return {"ok": True, "keywords": []}
    con = duckdb.connect(db_path)
    try:
        try:
            rows = con.execute('SELECT keyword, score FROM priority_keywords ORDER BY keyword').fetchall()
            cols = [c[0] for c in con.description]
            kws = [dict(zip(cols, r)) for r in rows]
            return {"ok": True, "keywords": kws}
        except Exception:
            return {"ok": True, "keywords": []}
    finally:
        con.close()


@app.post('/api/priority-keywords')
async def post_priority_keywords(payload: dict):
    items = payload.get('keywords', [])
    db_path = resolve_db_path()
    con = duckdb.connect(db_path)
    try:
        con.execute('CREATE TABLE IF NOT EXISTS priority_keywords (keyword TEXT PRIMARY KEY, score DOUBLE)')
        con.execute('DELETE FROM priority_keywords')
        for kw in items:
            if isinstance(kw, dict):
                keyword = kw.get('keyword')
                score = float(kw.get('score', 1.0))
            else:
                keyword = str(kw)
                score = 1.0
            if not keyword:
                continue
            con.execute('INSERT INTO priority_keywords (keyword, score) VALUES (?, ?)', (keyword, score))
        return {"ok": True, "count": len(items)}
    finally:
        con.close()


@app.get('/api/whatsapp/status')
async def whatsapp_status():
    return {"ok": True, "status": whatsapp_service.get_status()}


@app.post('/api/whatsapp/connect')
async def whatsapp_connect():
    # Set enabled in .env
    env_path = os.path.join(SECRETS_DIR, '.env')
    existing = {}
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    k, v = line.strip().split('=', 1)
                    existing[k] = v
    
    existing["WHATSAPP_ENABLED"] = "true"
    with open(env_path, 'w') as f:
        for k, v in existing.items():
            f.write(f"{k}={v}\n")
    
    whatsapp_service.start()
    return {"ok": True, "message": "WhatsApp service starting..."}


def format_stories_for_whatsapp(stories: list):
    if not stories:
        return "No new stories found today."
    
    msg = "*🚀 Nokast Top Stories*\n\n"
    for i, s in enumerate(stories[:5]):  # Send top 5 to keep message length manageable
        title = s.get('title', 'No Title')
        summary = s.get('summary', '')
        msg += f"*{i+1}. {title}*\n{summary}\n\n"
    
    msg += "Check the dashboard for more details!"
    return msg


def run_pipeline_job(newsletters: list, fetch_limit: int | None, notify_phone: str | None = None):
    global _last_run
    try:
        _last_run = {"running": True, "last_result": None}
        p = get_pipeline()
        if p is None:
            _last_run = {"running": False, "last_result": "pipeline_not_available"}
            return
        stories = p.run(fetch_limit=fetch_limit or None)
        _last_run = {"running": False, "last_result": "ok"}
        
        # WhatsApp Notification
        whatsapp_phone = notify_phone or os.getenv("WHATSAPP_PHONE")
        if whatsapp_phone and whatsapp_service.is_connected:
            formatted_msg = format_stories_for_whatsapp(stories)
            whatsapp_service.send_notification(whatsapp_phone, formatted_msg)

    except Exception as e:
        _last_run = {"running": False, "last_result": f"error: {e}"}


@app.post('/api/run')
async def run(req: RunRequest, background_tasks: BackgroundTasks):
    # Start pipeline in background to avoid blocking
    if not PIPELINE_AVAILABLE:
        return JSONResponse({"ok": False, "error": "pipeline_unavailable"}, status_code=500)

    fetch_limit = req.fetch_limit
    newsletters = req.newsletters or []
    # Start background task
    background_tasks.add_task(run_pipeline_job, newsletters, fetch_limit)
    return {"ok": True, "message": "pipeline_started"}


# Set up WhatsApp callback
def trigger_nokast_via_whatsapp(phone: str = None):
    # Run in background to avoid blocking WhatsApp client thread
    threading.Thread(target=run_pipeline_job, args=([], None, phone)).start()

whatsapp_service.on_nokast_callback = trigger_nokast_via_whatsapp


@app.get('/api/stories')
async def stories():
    # Read from DuckDB file used by pipeline
    db_path = resolve_db_path()
    if not os.path.exists(db_path):
        return {"ok": True, "stories": []}
    con = duckdb.connect(db_path)
    try:
        rows = con.execute('SELECT id, title, summary, linkedIn, x_post, branding_tag, action_suggestion, score, date_iso, sender_email, processed_at FROM top_stories ORDER BY processed_at DESC').fetchall()
        cols = [c[0] for c in con.description]
        stories = [dict(zip(cols, r)) for r in rows]
        return {"ok": True, "stories": stories}
    finally:
        con.close()


@app.post('/api/whatsapp/send-latest')
async def send_latest_to_whatsapp():
    """Send the 5 latest stories from DuckDB to the configured WhatsApp phone."""
    whatsapp_phone = os.getenv("WHATSAPP_PHONE")
    if not whatsapp_phone:
        return JSONResponse({"ok": False, "error": "WhatsApp phone not configured"}, status_code=400)
    
    if not whatsapp_service.is_connected:
        return JSONResponse({"ok": False, "error": "WhatsApp service not connected"}, status_code=400)

    db_path = resolve_db_path()
    if not os.path.exists(db_path):
        return JSONResponse({"ok": False, "error": "No stories found (database missing)"}, status_code=404)

    con = duckdb.connect(db_path)
    try:
        rows = con.execute('SELECT title, summary FROM top_stories ORDER BY processed_at DESC LIMIT 5').fetchall()
        if not rows:
            return JSONResponse({"ok": False, "error": "No stories found in database"}, status_code=404)
        
        stories = [{"title": r[0], "summary": r[1]} for r in rows]
        message = format_stories_for_whatsapp(stories)
        whatsapp_service.send_notification(whatsapp_phone, message)
        return {"ok": True, "message": f"Latest reports sent to {whatsapp_phone}"}
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)
    finally:
        con.close()


@app.get('/api/emails')
async def emails():
    db_path = resolve_db_path()
    if not os.path.exists(db_path):
        return {"ok": True, "emails": []}
    con = duckdb.connect(db_path)
    try:
        rows = con.execute('SELECT id, subject, sender_email, date_iso, substring(body,1,1000) as body, fetched_at FROM emails ORDER BY fetched_at DESC').fetchall()
        cols = [c[0] for c in con.description]
        emails = [dict(zip(cols, r)) for r in rows]
        return {"ok": True, "emails": emails}
    finally:
        con.close()


@app.post('/api/ai-helper')
async def ai_helper(payload: dict):
    # A simple wrapper to call the local ollama-based helper via pipeline functions
    p = get_pipeline()
    if p is None:
        return JSONResponse({"ok": False, "error": "pipeline_unavailable"}, status_code=500)
    # The pipeline module exposes generate_social etc. Use call_ollama helper if available
    try:
        from top_news_pipeline import call_ollama
        prompt = payload.get('prompt') or ''
        summary = payload.get('summary') or ''
        full_prompt = f"User prompt: {prompt}\n\nSummary:\n{summary}"
        res = call_ollama(full_prompt)
        return {"ok": True, "response": res}
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@app.get('/api/calendar/events')
async def get_calendar_events():
    """Fetch upcoming calendar events from Google Calendar."""
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        import googleapiclient.discovery
        from datetime import datetime, timedelta
        
        SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
        
        # Try to load credentials
        token_path = resolve_secret_path("GOOGLE_TOKEN", "token.json")
        credentials_path = resolve_secret_path("GOOGLE_CREDENTIALS", "Google_credentials.json")
        
        creds = None
        
        # Try to use OAuth token first (preferred for Calendar access)
        if os.path.exists(token_path):
            try:
                creds = Credentials.from_authorized_user_file(token_path, SCOPES)
                # Check if token is valid, refresh if expired
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                    # Save refreshed token
                    with open(token_path, 'w') as f:
                        f.write(creds.to_json())
            except Exception as e:
                print(f"[warn] Could not use OAuth token: {e}")
                creds = None
        
        # Fallback to service account credentials
        if creds is None and os.path.exists(credentials_path):
            try:
                from google.oauth2.service_account import Credentials as ServiceAccountCredentials
                creds = ServiceAccountCredentials.from_service_account_file(
                    credentials_path,
                    scopes=SCOPES
                )
            except Exception as e:
                print(f"[warn] Could not use service account credentials: {e}")
                creds = None
        
        # If no credentials found, try OAuth flow
        if creds is None and os.path.exists(credentials_path):
            try:
                from google_auth_oauthlib.flow import InstalledAppFlow
                flow = InstalledAppFlow.from_client_secrets_file(
                    credentials_path, 
                    SCOPES
                )
                # This will open a browser for user authentication
                creds = flow.run_local_server(port=0)
                # Save the token for future use
                with open(token_path, 'w') as f:
                    f.write(creds.to_json())
            except Exception as e:
                print(f"[warn] OAuth flow failed: {e}")
                creds = None
        
        if creds is None:
            return JSONResponse({"ok": False, "error": "Google credentials not configured"}, status_code=401)
        
        # Build Calendar service
        service = googleapiclient.discovery.build('calendar', 'v3', credentials=creds)
        
        # Get calendar events for the next 30 days
        now = datetime.utcnow().isoformat() + 'Z'
        thirty_days_later = (datetime.utcnow() + timedelta(days=30)).isoformat() + 'Z'
        
        events_result = service.events().list(
            calendarId='primary',
            timeMin=now,
            timeMax=thirty_days_later,
            maxResults=50,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        # Transform Google Calendar events to our format
        formatted_events = []
        for event in events:
            event_id = event.get('id', '')
            title = event.get('summary', 'Untitled Event')
            description = event.get('description', '')
            
            # Handle both dateTime (with time) and date (all-day events)
            start_info = event.get('start', {})
            end_info = event.get('end', {})
            
            if 'dateTime' in start_info:
                start_time = start_info['dateTime']
            elif 'date' in start_info:
                start_time = start_info['date'] + 'T00:00:00Z'
            else:
                start_time = now
            
            if 'dateTime' in end_info:
                end_time = end_info['dateTime']
            elif 'date' in end_info:
                end_time = end_info['date'] + 'T23:59:59Z'
            else:
                end_time = start_time
            
            organizer = event.get('organizer', {}).get('displayName', '')
            location = event.get('location', '')
            
            # Extract attendees
            attendees = []
            for attendee in event.get('attendees', []):
                display_name = attendee.get('displayName') or attendee.get('email', '')
                attendees.append(display_name)
            
            formatted_events.append({
                'id': event_id,
                'title': title,
                'description': description,
                'startTime': start_time,
                'endTime': end_time,
                'organizer': organizer,
                'location': location,
                'attendees': attendees
            })
        
        return {"ok": True, "events": formatted_events}
    
    except ImportError as e:
        return JSONResponse({"ok": False, "error": f"Missing required library: {str(e)}"}, status_code=500)
    except Exception as e:
        return JSONResponse({"ok": False, "error": f"Failed to fetch calendar events: {str(e)}"}, status_code=500)


if __name__ == '__main__':
    import uvicorn
    uvicorn.run('main:app', host='0.0.0.0', port=4000, reload=True)
