from langgraph.graph import StateGraph, END

from .state import TravelState
from .agents.init_parallel import init_parallel
from .agents.search_agent import live_search
from .agents.recommend_agent import recommend_hotels
from .database.store_results import store_results


def route_cache(state):
    if isinstance(state, dict):
        accommodations = state.get("accommodations") or []
    else:
        accommodations = getattr(state, "accommodations", []) or []

    if accommodations:
        return "recommend_hotels"
    return "live_search"


def build_graph():
    graph = StateGraph(TravelState)

    graph.add_node("init", init_parallel)
    graph.add_node("live_search", live_search)
    graph.add_node("store", store_results)
    graph.add_node("recommend_hotels", recommend_hotels)

    graph.set_entry_point("init")

    graph.add_conditional_edges(
        "init",
        route_cache,
        {
            "live_search": "live_search",
            "recommend_hotels": "recommend_hotels",
        },
    )

    graph.add_edge("live_search", "store")
    graph.add_edge("store", "recommend_hotels")

    graph.add_edge("recommend_hotels", END)

    return graph.compile()
