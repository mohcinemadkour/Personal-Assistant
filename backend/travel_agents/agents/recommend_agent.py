from urllib.parse import quote_plus


def _hotel_search_url(name: str, city: str, country: str | None = None) -> str:
    """Build a search URL that surfaces booking sites (Booking.com, Expedia, etc.)."""
    parts = [name, city]
    if country:
        parts.append(country)
    parts.append("book")
    q = " ".join(p for p in parts if p)
    return f"https://www.google.com/search?q={quote_plus(q)}"


def _hotel_map_url(name: str, city: str, country: str | None = None) -> str:
    """Build a Google Maps search URL for viewing the hotel on a map."""
    parts = [name, city]
    if country:
        parts.append(country)
    q = " ".join(p for p in parts if p)
    return f"https://www.google.com/maps/search/?api=1&query={quote_plus(q)}"


def recommend_hotels(state):
    """
    Sort accommodations by rating (desc), then price (asc),
    and pick top 5. Also replaces dummy URLs with real
    Google Search URLs for each hotel.
    """
    hotels = state.accommodations or []

    def score(h):
        rating = h.get("rating") or 0.0
        price = h.get("price") or h.get("price_per_night") or 0.0
        try:
            rating_f = float(rating)
        except Exception:
            rating_f = 0.0
        try:
            price_f = float(price)
        except Exception:
            price_f = 0.0
        # Higher rating, lower price
        return (-rating_f, price_f)

    hotels_sorted = sorted(hotels, key=score)
    top_hotels = hotels_sorted[:5]

    # Ensure each has a real, clickable URL (preserve existing booking/maps links from SerpAPI/Places)
    # Suppress serpapi.com links — they are API URLs, not user-facing booking pages
    for h in top_hotels:
        name = h.get("name") or ""
        city = h.get("city") or state.destination
        country = h.get("country") or ""
        url = (h.get("url") or "").strip()
        if not url or not url.startswith("http") or "serpapi.com" in url:
            h["url"] = _hotel_search_url(name, city, country)
        # map_url: use existing url if it's already a Google Maps link, else build one
        existing = (h.get("url") or "").strip()
        if "google.com/maps" in existing:
            h["map_url"] = existing
        else:
            h["map_url"] = _hotel_map_url(name, city, country)

    state.recommended_hotels = top_hotels
    return state
