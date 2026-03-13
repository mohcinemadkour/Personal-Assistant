import json
import os
from openai import OpenAI

from .places_client import fetch_hotels_from_places
from .serpapi_client import fetch_hotels_from_serpapi
from .destination_utils import resolve_destination_for_hotels

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def live_search(state):
    """
    Fetch accommodations (hotels).
    Hotels: SerpAPI (real prices) > Google Places > LLM.
    """
    accommodations_from_api = []
    destination = (state.destination or "").strip()
    hotel_destination = resolve_destination_for_hotels(destination) if destination else ""

    if hotel_destination and os.getenv("SERPAPI_API_KEY") and state.start_date and state.end_date:
        accommodations_from_api = fetch_hotels_from_serpapi(
            destination=hotel_destination,
            start_date=state.start_date,
            end_date=state.end_date,
            max_price_per_night=state.max_price_per_night,
            min_rating=state.min_rating,
            adults=2,
            limit=10,
        )
    elif hotel_destination and (os.getenv("GOOGLE_PLACES_API_KEY") or os.getenv("GOOGLE_MAPS_API_KEY")):
        accommodations_from_api = fetch_hotels_from_places(
            destination=hotel_destination,
            max_price_per_night=state.max_price_per_night,
            min_rating=state.min_rating,
            bedrooms=state.bedrooms or 1,
            limit=10,
        )

    if accommodations_from_api:
        state.accommodations = accommodations_from_api
        return state

    system_prompt = """
You are a travel planning AI. You help users find hotels.

You MUST respond with STRICT JSON only. No markdown, no explanations, no comments.
The JSON MUST have this exact structure:

{
  "accommodations": [
    {
      "name": "string",
      "city": "string",
      "country": "string",
      "price": 120.0,
      "rating": 8.5,
      "bedrooms": 1,
      "url": "https://..."
    }
  ]
}

Rules:
- All numbers must be valid JSON numbers (no commas in thousands, e.g. 1565.0 not 1,565.0).
- Return 3–7 accommodations.
- Try to respect user constraints (max price, min rating, bedrooms).
- Use realistic hotel names for the destination.
- For hotel prices: use approximate USD per-night rates typical for that city and star level. Stay within the user's max_price when provided. Prefer conservative estimates (slightly lower than typical) since users will verify on booking sites.
    """.strip()

    user_prompt = f"""
User trip details:
- Origin: {state.origin}
- Destination: {state.destination}
- Start date: {state.start_date}
- End date: {state.end_date}
- Bedrooms needed: {state.bedrooms}
- Max hotel price per night: {state.max_price_per_night}
- Minimum hotel rating: {state.min_rating}

Generate hotels that match these constraints as much as possible.

Return ONLY the JSON object as specified in the system message.
Do NOT include any additional keys, text, or markdown.
    """.strip()

    try:
        resp = client.chat.completions.create(
            model=os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
        )

        content = resp.choices[0].message.content.strip()

        if content.startswith("```"):
            parts = content.split("```")
            if len(parts) >= 3:
                content = parts[1]
            content = content.replace("json", "", 1).strip()

        cleaned = (
            content.replace(",}", "}")
                   .replace(",]", "]")
        )

        data = json.loads(cleaned)

        if isinstance(data, dict) and "accommodations" not in data:
            for key in ["result", "data", "response"]:
                if isinstance(data.get(key), dict):
                    data = data[key]
                    break

        accommodations = (
            data.get("accommodations")
            or data.get("hotels")
            or data.get("places")
            or []
        )

        if not isinstance(accommodations, list):
            accommodations = []

        state.accommodations = accommodations
        return state

    except Exception as e:
        print("[Warning] live_search error:", repr(e))
        state.accommodations = []
        return state
