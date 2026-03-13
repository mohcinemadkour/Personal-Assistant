"""Hotel suggestion service using local Travel Agent workflow."""

import os
import urllib.parse
from typing import Optional, List, Dict, Any


def generate_booking_url(
    hotel_name: str,
    destination: str,
    check_in: str,  # Format: YYYY-MM-DD
    check_out: str,  # Format: YYYY-MM-DD
    platform: str = "booking.com",
    hotel_url: Optional[str] = None,
) -> str:
    """
    Generate booking URL for the specified platform with date parameters.
    
    Args:
        hotel_name: Name of the hotel
        destination: Destination city
        check_in: Check-in date (YYYY-MM-DD)
        check_out: Check-out date (YYYY-MM-DD)
        platform: Booking platform ("booking.com", "expedia.com", "hotels.com", "native")
        hotel_url: Direct hotel URL if available
    
    Returns:
        Booking URL for the specified platform
    """
    if platform == "native" and hotel_url:
        # Use direct hotel URL if provided
        return hotel_url
    
    # Format search query
    search_query = f"{hotel_name} {destination}"
    
    if platform == "booking.com":
        # Booking.com URL format
        # https://www.booking.com/searchresults.html?ss=destination&checkin=YYYY-MM-DD&checkout=YYYY-MM-DD
        params = {
            "ss": destination,
            "checkin": check_in,
            "checkout": check_out,
        }
        return f"https://www.booking.com/searchresults.html?{urllib.parse.urlencode(params)}"
    
    elif platform == "expedia.com":
        # Expedia URL format
        # https://www.expedia.com/Hotel-Search?destination=destination&startDate=MM/DD/YYYY&endDate=MM/DD/YYYY
        # Convert YYYY-MM-DD to MM/DD/YYYY
        from datetime import datetime
        check_in_obj = datetime.strptime(check_in, "%Y-%m-%d")
        check_out_obj = datetime.strptime(check_out, "%Y-%m-%d")
        check_in_fmt = check_in_obj.strftime("%m/%d/%Y")
        check_out_fmt = check_out_obj.strftime("%m/%d/%Y")
        
        params = {
            "destination": destination,
            "startDate": check_in_fmt,
            "endDate": check_out_fmt,
        }
        return f"https://www.expedia.com/Hotel-Search?{urllib.parse.urlencode(params)}"
    
    elif platform == "hotels.com":
        # Hotels.com URL format
        params = {
            "destination": destination,
            "partialStay": "true",
            "checkin": check_in,
            "checkout": check_out,
        }
        return f"https://www.hotels.com/search/Hotel-{urllib.parse.quote(destination)}?{urllib.parse.urlencode(params)}"
    
    else:  # native or default
        # Fall back to Google search for the hotel + destination
        return f"https://www.google.com/search?q={urllib.parse.quote(search_query)}+{ urllib.parse.quote(check_in)}"


def get_hotel_suggestions(
    destination: str,
    start_date: str,  # Format: YYYY-MM-DD
    end_date: str,    # Format: YYYY-MM-DD
    bedrooms: int = 1,
    max_price_per_night: Optional[float] = 200.0,
    min_rating: Optional[float] = 4.0,
    origin: str = "US",
    booking_platform: str = "booking.com",
) -> List[Dict[str, Any]]:
    """
    Get hotel suggestions using local Travel Agent workflow.
    
    Args:
        destination: Destination city/location
        start_date: Check-in date (YYYY-MM-DD)
        end_date: Check-out date (YYYY-MM-DD)
        bedrooms: Number of bedrooms needed
        max_price_per_night: Maximum price per night in USD
        min_rating: Minimum hotel rating
        origin: Origin city/country
        booking_platform: Booking platform preference ("booking.com", "expedia.com", "hotels.com", "native")
    
    Returns:
        List of hotel recommendations with name, rating, price, url, map_url
    """
    try:
        # Import local travel agents
        from travel_agents.graph import build_graph
        from travel_agents.state import TravelState
        
        print(f"[info] Building travel graph for {destination}...")
        
        # Build the travel planning workflow
        graph = build_graph()
        
        # Create initial state
        initial_state = TravelState(
            origin=origin,
            destination=destination,
            start_date=start_date,
            end_date=end_date,
            bedrooms=bedrooms,
            max_price_per_night=max_price_per_night,
            min_rating=min_rating,
        )
        
        # Run the workflow
        print(f"[info] Invoking travel graph...")
        final_state = graph.invoke(initial_state)
        
        # Extract recommended hotels from the result
        if isinstance(final_state, dict):
            hotels = final_state.get("recommended_hotels", [])
        else:
            hotels = getattr(final_state, "recommended_hotels", []) or []
        
        print(f"[info] Got {len(hotels)} hotel recommendations")
        
        # Format hotels for frontend
        formatted_hotels = []
        for hotel in hotels:
            hotel_name = hotel.get("name", "")
            hotel_url = hotel.get("url", "")
            
            # Generate platform-specific booking URL
            booking_url = generate_booking_url(
                hotel_name=hotel_name,
                destination=destination,
                check_in=start_date,
                check_out=end_date,
                platform=booking_platform,
                hotel_url=hotel_url if booking_platform == "native" else None,
            )
            
            formatted_hotels.append({
                "name": hotel_name,
                "city": hotel.get("city", destination),
                "country": hotel.get("country", ""),
                "price_per_night": float(hotel.get("price") or hotel.get("price_per_night") or 0),
                "rating": float(hotel.get("rating") or 0),
                "bedrooms": int(hotel.get("bedrooms") or 1),
                "url": booking_url,
                "map_url": hotel.get("map_url", ""),
            })
        
        return formatted_hotels
    
    except Exception as e:
        print(f"[error] Failed to get hotel suggestions: {e}")
        import traceback
        traceback.print_exc()
        return _get_mock_hotels(destination, start_date, end_date, booking_platform)


def _get_mock_hotels(destination: str, start_date: str = "", end_date: str = "", booking_platform: str = "booking.com") -> List[Dict[str, Any]]:
    """Return mock hotel data when Travel Agent workflow is not available."""
    mock_hotels = [
        {"name": f"{destination} Premium Hotel", "city": destination, "country": "USA", "rating": 4.5},
        {"name": f"{destination} Comfort Inn", "city": destination, "country": "USA", "rating": 4.0},
        {"name": f"{destination} Luxury Resort", "city": destination, "country": "USA", "rating": 4.8},
    ]
    
    formatted = []
    prices = [180.0, 95.0, 280.0]
    
    for hotel, price in zip(mock_hotels, prices):
        hotel_name = hotel.get("name", "")
        booking_url = generate_booking_url(
            hotel_name=hotel_name,
            destination=destination,
            check_in=start_date or "2025-01-01",
            check_out=end_date or "2025-01-05",
            platform=booking_platform,
        )
        
        formatted.append({
            "name": hotel_name,
            "city": hotel.get("city", destination),
            "country": hotel.get("country", "USA"),
            "price_per_night": price,
            "rating": hotel.get("rating", 4.0),
            "bedrooms": 1,
            "url": booking_url,
            "map_url": f"https://www.google.com/maps/search/{destination}+hotels",
        })
    
    return formatted


def search_hotels_cached(
    destination: str,
    start_date: str,
    end_date: str,
    **kwargs
) -> List[Dict[str, Any]]:
    """
    Search for hotels with simple caching (in-memory for now).
    Can be extended with database caching later.
    """
    # For now, just call the main function
    # TODO: Add caching layer if needed
    return get_hotel_suggestions(destination, start_date, end_date, **kwargs)
