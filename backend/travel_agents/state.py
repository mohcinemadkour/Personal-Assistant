from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class TravelState(BaseModel):
    origin: Optional[str] = None
    destination: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None

    bedrooms: Optional[int] = 1
    max_price_per_night: Optional[float] = 200.0
    min_rating: Optional[float] = 4.0
    adults: Optional[int] = 2
    children: Optional[int] = 0
    sort_by: Optional[str] = "rating"   # "rating" | "price"
    currency: Optional[str] = "USD"

    weather_summary: Optional[str] = None
    accommodations: List[Dict[str, Any]] = []
    recommended_hotels: List[Dict[str, Any]] = []
