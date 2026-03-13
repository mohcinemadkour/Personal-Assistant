"""Resolve destination for hotel search."""

_FALLBACK_IATA_TO_CITY = {
    "BOM": "Mumbai",
    "BLR": "Bengaluru",
    "DEL": "New Delhi",
    "MAA": "Chennai",
    "HYD": "Hyderabad",
    "CCU": "Kolkata",
    "JFK": "New York",
    "LHR": "London",
    "CDG": "Paris",
    "DXB": "Dubai",
    "SIN": "Singapore",
    "BKK": "Bangkok",
    "HKG": "Hong Kong",
    "ICN": "Seoul",
    "NRT": "Tokyo",
    "HND": "Tokyo",
    "SYD": "Sydney",
    "LAX": "Los Angeles",
    "SFO": "San Francisco",
    "MCO": "Orlando",
    "ORD": "Chicago",
    "ATL": "Atlanta",
    "DFW": "Dallas",
    "MIA": "Miami",
    "SEA": "Seattle",
    "DEN": "Denver",
    "EWR": "Newark",
    "LGA": "New York",
    "FLL": "Fort Lauderdale",
    "IAD": "Washington",
    "DCA": "Washington",
    "PHX": "Phoenix",
    "MSP": "Minneapolis",
    "DTW": "Detroit",
    "PHL": "Philadelphia",
    "BOS": "Boston",
    "CLT": "Charlotte",
    "SAN": "San Diego",
    "TPA": "Tampa",
    "IAH": "Houston",
    "AUS": "Austin",
    "PDX": "Portland",
    "STL": "St. Louis",
    "MCI": "Kansas City",
    "RDU": "Raleigh",
    "BNA": "Nashville",
    "SLC": "Salt Lake City",
    "CUN": "Cancún",
    "MEX": "Mexico City",
    "GRU": "São Paulo",
    "EZE": "Buenos Aires",
    "BOG": "Bogotá",
    "LIM": "Lima",
    "FCO": "Rome",
    "AMS": "Amsterdam",
    "FRA": "Frankfurt",
    "MUC": "Munich",
    "MAD": "Madrid",
    "BCN": "Barcelona",
    "IST": "Istanbul",
    "DOH": "Doha",
    "AUH": "Abu Dhabi",
    "KUL": "Kuala Lumpur",
    "MNL": "Manila",
    "CGK": "Jakarta",
    "PEK": "Beijing",
    "PVG": "Shanghai",
    "TPE": "Taipei",
    "NBO": "Nairobi",
    "JNB": "Johannesburg",
    "CAI": "Cairo",
    "CPT": "Cape Town",
}


def _looks_like_iata(text: str) -> bool:
    if not text or len(text) != 3:
        return False
    return text.strip().isalpha()


def resolve_destination_for_hotels(destination: str) -> str:
    """
    Resolve destination to a city name suitable for hotel search.
    - If destination looks like IATA (3 letters): resolve to city name.
    - Otherwise: return as-is (assume it's already a city/place name).
    """
    if not destination:
        return ""
    dest = destination.strip()
    if not _looks_like_iata(dest):
        return dest

    iata = dest.upper()
    city = _FALLBACK_IATA_TO_CITY.get(iata)
    if city:
        return city
    return dest
