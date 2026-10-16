from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings


def _connect_args(url: str) -> dict:
    # SQLite (used only by the test-suite) refuses to share a connection across threads by
    # default, and Starlette's TestClient drives the app from a worker thread. PostgreSQL
    # must not receive this flag, so it is added only for sqlite URLs.
    return {"check_same_thread": False} if url.startswith("sqlite") else {}


# pool_pre_ping makes the pool test a connection before handing it out, so the API recovers
# cleanly when PostgreSQL restarts (for example after a rolling update in Kubernetes).
engine = create_engine(settings.database_url, pool_pre_ping=True, connect_args=_connect_args(settings.database_url))
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency: one session per request, always closed afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
