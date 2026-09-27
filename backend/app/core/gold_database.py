"""Read-only connection to the gold database (DOC-13 skill trends).

Gold is built by dbt in the scraper warehouse and copied to its own
PostgreSQL database (GOLD_DATABASE_URL); the backend only reads it. It is
separate from the site database, so it has its own lazily created engine.
"""
import os
from collections.abc import Generator
from threading import Lock

from fastapi import HTTPException, status
from sqlalchemy import Connection, Engine, create_engine

from app.core.config import settings

_engine: Engine | None = None
_engine_lock = Lock()


def get_gold_engine() -> Engine | None:
    global _engine
    if settings.gold_database_url is None:
        return None
    with _engine_lock:
        if _engine is None:
            # Same sizing rule as the site database: one connection per
            # short-lived Vercel instance, a small pool elsewhere.
            pool = {"pool_size": 1, "max_overflow": 0} if os.getenv("VERCEL") is not None else {"pool_size": 2, "max_overflow": 2}
            _engine = create_engine(settings.gold_database_url, pool_pre_ping=True, pool_recycle=300, **pool)
    return _engine


def get_gold_connection() -> Generator[Connection, None, None]:
    engine = get_gold_engine()
    if engine is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Skill trends are not configured")
    with engine.connect() as connection:
        yield connection
