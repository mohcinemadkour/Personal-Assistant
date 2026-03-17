"""
Resolve destination for hotel search.
When user provides an airport code (e.g. MCO, JFK), resolve to city name
so hotel APIs return relevant results.
Uses airports.csv / airport-codes.csv; falls back to a static mapping.
"""

import csv
import os

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


def _load_iata_to_city_from_csv() -> dict[str, str]:
    """Load IATA -> city mapping from airports.csv or airport-codes.csv."""
    iata_to_city: dict[str, tuple[str, int]] = {}
    priority = {"large_airport": 3, "medium_airport": 2, "small_airport": 1}
    csv_names = ["airports.csv", "airport-codes.csv"]

    # Check both the backend root and cwd
    search_dirs = [
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        os.getcwd(),
    ]
    for base in search_dirs:
        for csv_name in csv_names:
            path = os.path.join(base, csv_name)
            if not os.path.isfile(path):
                continue
            try:
                with open(path, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        iata = (row.get("iata_code") or "").strip()
                        city = (row.get("municipality") or "").strip()
                        if iata and len(iata) == 3 and iata.isalpha() and city:
                            p = priority.get(row.get("type", ""), 0)
                            if iata not in iata_to_city or p > iata_to_city[iata][1]:
                                iata_to_city[iata] = (city, p)
                if iata_to_city:
                    return {k: v[0] for k, v in iata_to_city.items()}
            except Exception:
                pass
    return {}


_IATA_TO_CITY_CACHE: dict[str, str] | None = None


def _get_iata_to_city() -> dict[str, str]:
    global _IATA_TO_CITY_CACHE
    if _IATA_TO_CITY_CACHE is None:
        _IATA_TO_CITY_CACHE = _load_iata_to_city_from_csv()
        if not _IATA_TO_CITY_CACHE:
            _IATA_TO_CITY_CACHE = _FALLBACK_IATA_TO_CITY.copy()
    return _IATA_TO_CITY_CACHE


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
    iata_to_city = _get_iata_to_city()
    city = iata_to_city.get(iata)
    if city:
        return city
    return dest
