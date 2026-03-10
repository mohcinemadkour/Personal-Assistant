import os
import json
import datetime
from pathlib import Path

import streamlit as st
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
TOKEN_PATH = Path("token.json")
CREDENTIALS_PATH = Path("Gmail_Credential.json")

st.set_page_config(
    page_title="Google Calendar – This Week",
    page_icon="📅",
    layout="wide",
)

# ── Styles ──────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    .event-card {
        background: linear-gradient(135deg, #ffffff 0%, #f8f9ff 100%);
        border-left: 4px solid #4285f4;
        border-radius: 10px;
        padding: 1.2rem 1.5rem;
        margin-bottom: 0.8rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .event-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 16px rgba(0,0,0,0.10);
    }
    .event-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #1a1a2e;
        margin-bottom: 0.3rem;
    }
    .event-time {
        font-size: 0.92rem;
        color: #4285f4;
        font-weight: 500;
    }
    .event-location {
        font-size: 0.85rem;
        color: #666;
        margin-top: 0.2rem;
    }
    .day-header {
        font-size: 1.25rem;
        font-weight: 700;
        color: #1a1a2e;
        margin-top: 1.5rem;
        margin-bottom: 0.6rem;
        padding-bottom: 0.3rem;
        border-bottom: 2px solid #e8eaed;
    }
    .stat-box {
        background: linear-gradient(135deg, #4285f4 0%, #5e97f6 100%);
        color: white;
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
    }
    .stat-number { font-size: 2rem; font-weight: 700; }
    .stat-label  { font-size: 0.85rem; opacity: 0.9; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ── Auth helpers ────────────────────────────────────────────────────────────────
def get_credentials() -> Credentials | None:
    """Return valid Google credentials, refreshing or running the OAuth flow as needed."""
    creds = None

    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            TOKEN_PATH.write_text(creds.to_json())
            return creds
        except Exception:
            TOKEN_PATH.unlink(missing_ok=True)

    if not CREDENTIALS_PATH.exists():
        return None

    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
    creds = flow.run_local_server(port=0)
    TOKEN_PATH.write_text(creds.to_json())
    return creds


def get_week_bounds() -> tuple[datetime.datetime, datetime.datetime]:
    """Return (start_of_week_monday, end_of_week_sunday) in UTC."""
    today = datetime.date.today()
    monday = today - datetime.timedelta(days=today.weekday())
    sunday = monday + datetime.timedelta(days=6, hours=23, minutes=59, seconds=59)
    start = datetime.datetime.combine(monday, datetime.time.min).astimezone(
        datetime.timezone.utc
    )
    end = datetime.datetime.combine(sunday, datetime.time(23, 59, 59)).astimezone(
        datetime.timezone.utc
    )
    return start, end


def fetch_events(creds: Credentials) -> list[dict]:
    """Fetch all calendar events for the current week."""
    service = build("calendar", "v3", credentials=creds)
    start, end = get_week_bounds()

    events_result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=start.isoformat(),
            timeMax=end.isoformat(),
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    return events_result.get("items", [])


def parse_event_dt(event: dict, key: str) -> datetime.datetime | None:
    """Parse start/end datetime from an event dict."""
    raw = event.get(key, {})
    dt_str = raw.get("dateTime")
    if dt_str:
        return datetime.datetime.fromisoformat(dt_str)
    date_str = raw.get("date")
    if date_str:
        return datetime.datetime.fromisoformat(date_str)
    return None


# ── UI ──────────────────────────────────────────────────────────────────────────
st.title("📅 Google Calendar — This Week")

if not CREDENTIALS_PATH.exists():
    st.error(
        "**credentials.json** not found in the project folder.\n\n"
        "1. Go to the [Google Cloud Console](https://console.cloud.google.com/apis/credentials).\n"
        "2. Create an **OAuth 2.0 Client ID** (Desktop application).\n"
        "3. Download the JSON and save it as `credentials.json` in this project's root directory.\n"
        "4. Make sure the **Google Calendar API** is enabled for your project."
    )
    st.stop()

if st.button("🔄 Connect / Refresh Calendar", type="primary"):
    st.session_state.pop("events", None)
    st.session_state.pop("creds_ok", None)

creds = get_credentials()

if creds is None:
    st.info("Click **Connect / Refresh Calendar** to authenticate with Google.")
    st.stop()

st.session_state["creds_ok"] = True

with st.spinner("Fetching events…"):
    events = fetch_events(creds)

# ── Summary stats ───────────────────────────────────────────────────────────────
start, end = get_week_bounds()
all_day_count = sum(1 for e in events if "date" in e.get("start", {}))
timed_count = len(events) - all_day_count

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(
        f'<div class="stat-box"><div class="stat-number">{len(events)}</div>'
        f'<div class="stat-label">Total Events</div></div>',
        unsafe_allow_html=True,
    )
with col2:
    st.markdown(
        f'<div class="stat-box"><div class="stat-number">{timed_count}</div>'
        f'<div class="stat-label">Scheduled</div></div>',
        unsafe_allow_html=True,
    )
with col3:
    st.markdown(
        f'<div class="stat-box"><div class="stat-number">{all_day_count}</div>'
        f'<div class="stat-label">All-Day</div></div>',
        unsafe_allow_html=True,
    )

st.markdown("---")

# ── Event list grouped by day ───────────────────────────────────────────────────
if not events:
    st.info("No events found for this week. Enjoy the free time!")
    st.stop()

events_by_day: dict[str, list[dict]] = {}
for event in events:
    dt = parse_event_dt(event, "start")
    day_label = dt.strftime("%A, %B %d") if dt else "Unknown"
    events_by_day.setdefault(day_label, []).append(event)

for day, day_events in events_by_day.items():
    st.markdown(f'<div class="day-header">{day}</div>', unsafe_allow_html=True)

    for event in day_events:
        summary = event.get("summary", "(No title)")
        location = event.get("location", "")
        start_dt = parse_event_dt(event, "start")
        end_dt = parse_event_dt(event, "end")

        if "dateTime" in event.get("start", {}):
            time_str = (
                f"{start_dt.strftime('%I:%M %p')} – {end_dt.strftime('%I:%M %p')}"
                if end_dt
                else start_dt.strftime("%I:%M %p")
            )
        else:
            time_str = "All day"

        location_html = (
            f'<div class="event-location">📍 {location}</div>' if location else ""
        )

        st.markdown(
            f"""
            <div class="event-card">
                <div class="event-title">{summary}</div>
                <div class="event-time">🕐 {time_str}</div>
                {location_html}
            </div>
            """,
            unsafe_allow_html=True,
        )
