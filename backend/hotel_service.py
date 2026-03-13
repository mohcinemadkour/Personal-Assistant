"""Hotel suggestion service using local Travel Agent workflow."""

import os
from typing import Optional, List, Dict, Any


def get_hotel_suggestions(
    destination: str,
    start_date: str,  # Format: YYYY-MM-DD
    end_date: str,    # Format: YYYY-MM-DD
    bedrooms: int = 1,
    max_price_per_night: Optional[float] = 200.0,
    min_rating: Optional[float] = 4.0,
    origin: str = "US",
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
            formatted_hotels.append({
                "name": hotel.get("name", ""),
                "city": hotel.get("city", destination),
                "country": hotel.get("country", ""),
                "price_per_night": float(hotel.get("price") or hotel.get("price_per_night") or 0),
                "rating": float(hotel.get("rating") or 0),
                "bedrooms": int(hotel.get("bedrooms") or 1),
                "url": hotel.get("url", ""),
                "map_url": hotel.get("map_url", ""),
            })
        
        return formatted_hotels
    
    except Exception as e:
        print(f"[error] Failed to get hotel suggestions: {e}")
        import traceback
        traceback.print_exc()
        return _get_mock_hotels(destination)


def _get_mock_hotels(destination: str) -> List[Dict[str, Any]]:
    """Return mock hotel data when Travel Agent workflow is not available."""
    return [
        {
            "name": f"{destination} Premium Hotel",
            "city": destination,
            "country": "USA",
            "price_per_night": 180.0,
            "rating": 4.5,
            "bedrooms": 1,
            "url": f"https://www.google.com/search?q={destination}+hotels+book",
            "map_url": f"https://www.google.com/maps/search/{destination}+hotels",
        },
        {
            "name": f"{destination} Comfort Inn",
            "city": destination,
            "country": "USA",
            "price_per_night": 95.0,
            "rating": 4.0,
            "bedrooms": 1,
            "url": f"https://www.google.com/search?q={destination}+hotels+book",
            "map_url": f"https://www.google.com/maps/search/{destination}+hotels",
        },
        {
            "name": f"{destination} Luxury Resort",
            "city": destination,
            "country": "USA",
            "price_per_night": 280.0,
            "rating": 4.8,
            "bedrooms": 1,
            "url": f"https://www.google.com/search?q={destination}+hotels+book",
            "map_url": f"https://www.google.com/maps/search/{destination}+hotels",
        },
    ]


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
