from .singlestore_client import get_conn


def store_results(state):
    """Store freshly fetched accommodations into SingleStore."""
    conn = get_conn()
    if not conn:
        return state
    
    try:
        cur = conn.cursor()

        for h in state.accommodations:
            cur.execute(
                """
                INSERT INTO accommodations
                    (name, location_city, location_country, price_per_night, rating, url, bedrooms)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    h.get("name"),
                    h.get("city") or h.get("location_city"),
                    h.get("country") or h.get("location_country"),
                    h.get("price") or h.get("price_per_night"),
                    h.get("rating"),
                    h.get("url"),
                    h.get("bedrooms"),
                ),
            )

        conn.commit()
    except Exception as e:
        print(f"[Info] Store results error: {e}")
    
    return state
