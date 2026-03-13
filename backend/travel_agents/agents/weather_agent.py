import requests

def fetch_weather(state):
    """Fetch weather using Open-Meteo based on destination."""

    # 1. Get coordinates
    try:
        geo = requests.get(
            f"https://geocoding-api.open-meteo.com/v1/search?name={state.destination}"
        ).json()

        lat = geo["results"][0]["latitude"]
        lon = geo["results"][0]["longitude"]

    except:
        # fallback: Mumbai
        lat, lon = 19.0760, 72.8777

    # 2. Get temperatures
    weather_url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}&daily=temperature_2m_max,temperature_2m_min"
        f"&timezone=auto"
    )

    try:
        data = requests.get(weather_url).json()

        max_t = max(data["daily"]["temperature_2m_max"])
        min_t = min(data["daily"]["temperature_2m_min"])

        summary = f"Temperature ranges between {min_t:.1f}°C and {max_t:.1f}°C."

    except:
        summary = "Weather unavailable."

    state.weather_summary = summary
    return state
