from concurrent.futures import ThreadPoolExecutor

from .weather_agent import fetch_weather
from ..database.cache import check_cache


def init_parallel(state):
    """
    Run weather fetch and cache check in parallel, then merge results.
    """
    state_weather = state.model_copy(deep=True)
    state_cache = state.model_copy(deep=True)

    def run_weather():
        return fetch_weather(state_weather)

    def run_cache():
        return check_cache(state_cache)

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_weather = executor.submit(run_weather)
        future_cache = executor.submit(run_cache)
        result_weather = future_weather.result()
        result_cache = future_cache.result()

    state.weather_summary = result_weather.weather_summary
    if result_cache is not None:
        state.accommodations = result_cache.accommodations or []
    return state
