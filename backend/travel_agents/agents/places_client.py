import os
import requests
from urllib.parse import quote_plus


def _geocode_destination(destination: str, api_key: str) -> tuple[float, float] | None:
    """Get lat,lng for a city/destination using Geocoding API."""
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": destination, "key": api_key}
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        results = data.get("results") or []
        if results:
            loc = results[0].get("geometry", {}).get("location", {})
            return (loc.get("lat"), loc.get("lng"))
    except Exception:
        pass
    return None


def _price_level_to_estimate(level: int | None) -> float | None:
    """Convert Google price_level (0-4) to approximate USD per night."""
    if level is None:
        return None
    estimates = {0: 0, 1: 50, 2: 100, 3: 175, 4: 300}
    return float(estimates.get(level, 100))


def fetch_hotels_from_places(
    destination: str,
    max_price_per_night: float | None = None,
    min_rating: float | None = None,
    bedrooms: int = 1,
    limit: int = 10,
) -> list[dict]:
    """Fetch hotels from Google Places API."""
    api_key = os.getenv("GOOGLE_PLACES_API_KEY") or os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return []

    query = f"hotels in {destination}"
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {
        "query": query,
        "type": "lodging",
        "key": api_key,
    }

    coords = _geocode_destination(destination, api_key)
    if coords and coords[0] and coords[1]:
        params["location"] = f"{coords[0]},{coords[1]}"
        params["radius"] = 50000

    if max_price_per_night is not None:
        if max_price_per_night < 50:
            params["maxprice"] = 1
        elif max_price_per_night < 100:
            params["maxprice"] = 2
        elif max_price_per_night < 200:
            params["maxprice"] = 3
        else:
            params["maxprice"] = 4

    try:
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"[Info] Google Places search: {e!r}")
        return []

    if data.get("status") not in ("OK", "ZERO_RESULTS"):
        print(f"[Info] Google Places: {data.get('status', 'unknown')}")
        return []

    results = data.get("results") or []
    hotels = []

    for p in results[:limit]:
        name = p.get("name") or ""
        if not name:
            continue

        rating = p.get("rating")
        try:
            rating_f = float(rating) if rating is not None else None
        except (TypeError, ValueError):
            rating_f = None

        if min_rating is not None and rating_f is not None and rating_f < min_rating:
            continue

        price_level = p.get("price_level")
        price = _price_level_to_estimate(price_level)

        place_id = p.get("place_id") or ""
        formatted_address = p.get("formatted_address") or ""

        parts = [s.strip() for s in formatted_address.split(",") if s.strip()]
        city = parts[-2] if len(parts) >= 2 else destination
        country = parts[-1] if len(parts) >= 1 else ""

        maps_url = f"https://www.google.com/maps/search/?api=1&query={quote_plus(name + ' ' + destination)}"
        if place_id:
            maps_url = f"https://www.google.com/maps/place/?q=place_id:{place_id}"

        photo_url = None
        photos = p.get("photos") or []
        if photos:
            ref = photos[0].get("photo_reference")
            if ref:
                photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photo_reference={ref}&key={api_key}"

        hotels.append({
            "name": name,
            "address": formatted_address,
            "city": city,
            "country": country,
            "price": price,
            "price_per_night": price,
            "rating": rating_f,
            "user_ratings_total": p.get("user_ratings_total"),
            "url": maps_url,
            "photo_url": photo_url,
            "place_id": place_id,
            "formatted_address": formatted_address,
            "bedrooms": bedrooms,
        })

    return hotels
