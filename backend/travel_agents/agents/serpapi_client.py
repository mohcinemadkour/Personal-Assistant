import os
import requests


def fetch_hotels_from_serpapi(
    destination: str,
    start_date: str,
    end_date: str,
    max_price_per_night: float | None = None,
    min_rating: float | None = None,
    adults: int = 2,
    limit: int = 10,
) -> list[dict]:
    """Fetch hotels with real prices from SerpAPI Google Hotels."""
    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        return []

    url = "https://serpapi.com/search"
    params = {
        "engine": "google_hotels",
        "api_key": api_key,
        "q": f"hotels in {destination}",
        "check_in_date": start_date,
        "check_out_date": end_date,
        "adults": adults,
        "currency": "USD",
    }

    if max_price_per_night is not None:
        params["max_price"] = int(max_price_per_night)
    if min_rating is not None:
        if min_rating >= 4.5:
            params["rating"] = 9
        elif min_rating >= 4.0:
            params["rating"] = 8
        elif min_rating >= 3.5:
            params["rating"] = 7

    try:
        r = requests.get(url, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"[Info] SerpAPI Google Hotels: {e!r}")
        return []

    if data.get("error"):
        print(f"[Info] SerpAPI: {data.get('error')}")
        return []

    hotels = []
    seen_names: set[str] = set()

    def _add_hotel(
        name: str,
        price: float | None,
        rating: float | None,
        reviews: int | None,
        link: str | None,
        thumbnail: str | None,
        source: str | None = None,
    ):
        if not name or name.lower() in seen_names:
            return
        if min_rating is not None and rating is not None and rating < min_rating:
            return
        if max_price_per_night is not None and price is not None and price > max_price_per_night:
            return
        seen_names.add(name.lower())
        hotels.append({
            "name": name,
            "city": destination,
            "country": "",
            "price": price,
            "price_per_night": price,
            "rating": rating,
            "user_ratings_total": reviews,
            "url": link or "",
            "photo_url": thumbnail,
            "source": source,
            "bedrooms": 1,
        })

    # Ads (sponsored results)
    for ad in data.get("ads") or []:
        name = ad.get("name") or ""
        price = ad.get("extracted_price")
        if price is None:
            price_str = ad.get("price")
            if price_str and isinstance(price_str, str):
                try:
                    price = float(price_str.replace("$", "").replace(",", "").strip())
                except (ValueError, TypeError):
                    pass
        rating = ad.get("overall_rating")
        reviews = ad.get("reviews")
        link = ad.get("link") or ad.get("serpapi_property_details_link")
        thumbnail = (ad.get("images") or [{}])[0].get("thumbnail") if ad.get("images") else ad.get("thumbnail")
        _add_hotel(name, price, rating, reviews, link, thumbnail, ad.get("source"))

    # Properties (organic results)
    for prop in data.get("properties") or []:
        name = prop.get("name") or ""
        rate = prop.get("rate_per_night") or {}
        price = rate.get("extracted_lowest")
        if price is None:
            total = prop.get("total_rate") or {}
            price = total.get("extracted_lowest")
        rating = prop.get("overall_rating")
        reviews = prop.get("reviews")
        link = prop.get("link") or prop.get("serpapi_property_details_link")
        images = prop.get("images") or []
        thumbnail = images[0].get("thumbnail") or images[0].get("original_image") if images else None
        _add_hotel(name, price, rating, reviews, link, thumbnail)

    return hotels[:limit]
