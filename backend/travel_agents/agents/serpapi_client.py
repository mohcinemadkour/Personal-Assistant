import os
import requests
from urllib.parse import urlparse, parse_qs, unquote


def _extract_direct_url(google_redirect: str) -> str:
    """
    Extract the actual booking URL from a google.com/travel/clk redirect.
    The destination URL is in the `pcurl` query parameter.
    Returns the decoded direct URL, or the original redirect if parsing fails.
    """
    try:
        parsed = urlparse(google_redirect)
        params = parse_qs(parsed.query)
        pcurl = params.get("pcurl", [None])[0]
        if pcurl and pcurl.startswith("http"):
            return unquote(pcurl)
    except Exception:
        pass
    return google_redirect


def _fetch_expedia_link(serpapi_details_url: str, api_key: str) -> str | None:
    """
    Call the SerpAPI property details endpoint and return the Expedia direct booking
    link from the `prices` list, falling back to any other direct booking link found.
    """
    if not serpapi_details_url or not serpapi_details_url.startswith("http"):
        return None
    try:
        r = requests.get(serpapi_details_url, params={"api_key": api_key}, timeout=15)
        r.raise_for_status()
        data = r.json()
        if data.get("error"):
            print(f"[Info] Property details: {data.get('error')}")
            return None
        prices = data.get("prices") or []
        fallback = None
        for price in prices:
            link = (price.get("link") or "").strip()
            source = (price.get("source") or "").lower()
            if not link or not link.startswith("http"):
                continue
            direct = _extract_direct_url(link)
            if "expedia" in source:
                return direct
            if fallback is None:
                fallback = direct
        return fallback
    except Exception as e:
        print(f"[Info] Property details fetch: {e!r}")
    return None


def fetch_hotels_from_serpapi(
    destination: str,
    start_date: str,
    end_date: str,
    max_price_per_night: float | None = None,
    min_rating: float | None = None,
    adults: int = 2,
    children: int = 0,
    sort_by: str = "rating",
    currency: str = "USD",
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
        "currency": currency,
    }

    if children > 0:
        params["children"] = children

    # sort_by: 3=lowest price, 8=highest rated
    if sort_by == "price":
        params["sort_by"] = 3
    else:
        params["sort_by"] = 8

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
        address: str | None = None,
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
            "address": address or "",
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
        details_url = ad.get("serpapi_property_details_link") or ""
        expedia_link = _fetch_expedia_link(details_url, api_key) if details_url else None
        link = expedia_link or ad.get("link") or ""
        thumbnail = (ad.get("images") or [{}])[0].get("thumbnail") if ad.get("images") else ad.get("thumbnail")
        address = ad.get("address") or ad.get("neighborhood") or None
        _add_hotel(name, price, rating, reviews, link, thumbnail, ad.get("source"), address)

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
        details_url = prop.get("serpapi_property_details_link") or ""
        expedia_link = _fetch_expedia_link(details_url, api_key) if details_url else None
        link = expedia_link or prop.get("link") or ""
        images = prop.get("images") or []
        thumbnail = images[0].get("thumbnail") or images[0].get("original_image") if images else None
        address = prop.get("address") or prop.get("neighborhood") or None
        _add_hotel(name, price, rating, reviews, link, thumbnail, None, address)

    return hotels[:limit]
