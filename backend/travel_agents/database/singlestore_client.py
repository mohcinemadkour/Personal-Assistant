"""SingleStore client for hotel caching."""

import os

_conn = None


def get_conn():
    """Get or create SingleStore connection (gracefully handle unavailable DB)."""
    global _conn
    
    if _conn is not None:
        return _conn
    
    # Try to connect, but fail gracefully if DB not available
    try:
        import singlestoredb as s2
        
        host = os.getenv("SINGLESTORE_HOST")
        user = os.getenv("SINGLESTORE_USER")
        password = os.getenv("SINGLESTORE_PASSWORD")
        database = os.getenv("SINGLESTORE_DATABASE", "traveldb")
        
        if not all([host, user, password]):
            return None
        
        _conn = s2.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            autocommit=False,
        )
        
        # Create accommodations table if it doesn't exist
        cur = _conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS accommodations (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255),
                location_city VARCHAR(255),
                location_country VARCHAR(255),
                price_per_night FLOAT,
                rating FLOAT,
                url TEXT,
                bedrooms INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_city (location_city)
            )
        """)
        _conn.commit()
        return _conn
    
    except Exception as e:
        print(f"[Info] SingleStore not available: {e}")
        return None
