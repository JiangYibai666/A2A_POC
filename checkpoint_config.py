"""
Configure a PostgreSQL checkpointer for persisted LangGraph state.
"""

from langgraph.checkpoint.postgres import PostgresSaver
from psycopg_pool import ConnectionPool
import os
from dotenv import load_dotenv

load_dotenv()

def get_postgres_checkpointer():
    """Create a PostgreSQL checkpointer instance."""
    DB_URI = os.getenv("DATABASE_URL", "postgresql://localhost:5432/langgraph")
    
    # Create the connection pool.
    pool = ConnectionPool(
        conninfo=DB_URI,
        max_size=10,
        kwargs={"autocommit": True}
    )
    
    # Create the checkpointer and initialize the required tables.
    checkpointer = PostgresSaver(pool)
    checkpointer.setup()  # Automatically create the required tables.
    
    return checkpointer


# Example usage to replace MemorySaver in supervisor_app.py.
if __name__ == "__main__":
    checkpointer = get_postgres_checkpointer()
    print("PostgreSQL checkpointer configured")