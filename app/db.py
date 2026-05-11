import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

_engine = None


def get_engine():
    """Return a singleton SQLAlchemy engine with connection pooling."""
    global _engine
    if _engine is None:
        url = os.getenv("DATABASE_URL")
        if not url:
            raise ValueError("DATABASE_URL environment variable is not set.")
        _engine = create_engine(
            url,
            pool_size=2,
            max_overflow=2,
            pool_pre_ping=True,   # drops stale connections before use
            pool_recycle=300,     # recycle connections every 5 min (Neon safe)
        )
    return _engine
