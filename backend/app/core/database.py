from collections.abc import Generator
from pathlib import Path
from time import monotonic

from sqlalchemy import create_engine, event, exc
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import settings

SQLALCHEMY_DATABASE_URL = settings.database_url
if not SQLALCHEMY_DATABASE_URL:
    # Without this, create_engine(None) fails with an opaque
    # "Expected string or URL object, got None" instead of naming the
    # actual missing setting.
    raise RuntimeError("DATABASE_URL is not set")

_IS_POSTGRES = SQLALCHEMY_DATABASE_URL.startswith("postgres")

_engine_kwargs: dict = {}
if _IS_POSTGRES:
    _engine_kwargs = {
        "pool_pre_ping": False,
        "pool_recycle": 300,
        "pool_size": 5,
        "max_overflow": 5,
        "pool_use_lifo": True,
    }

engine = create_engine(SQLALCHEMY_DATABASE_URL, **_engine_kwargs)

# Hosted Postgres is ~250ms away; pinging on every checkout added a full
# round-trip to each API request. Recycle idle sockets and only ping when
# a connection has sat unused long enough that the pooler may have dropped it.
_IDLE_PING_AFTER_SECONDS = 30


def _register_idle_ping_listeners(engine) -> None:
    @event.listens_for(engine, "checkout")
    def _ping_if_idle(dbapi_connection, connection_record, _connection_proxy):
        last_ok = connection_record.info.get("last_ok")
        if last_ok is not None and monotonic() - last_ok < _IDLE_PING_AFTER_SECONDS:
            return
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        except Exception as error:
            connection_record.invalidate(error)
            raise exc.DisconnectionError() from error
        finally:
            cursor.close()
        connection_record.info["last_ok"] = monotonic()

    @event.listens_for(engine, "checkin")
    def _mark_checkin(_dbapi_connection, connection_record):
        connection_record.info["last_ok"] = monotonic()


if _IS_POSTGRES:
    _register_idle_ping_listeners(engine)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()

_SQL_DIR = Path(__file__).resolve().parent.parent / "sql"


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def seed_db() -> None:
    """Inject company seed SQL on every server start."""
    sql = (_SQL_DIR / "seed_companies.sql").read_text(encoding="utf-8")
    with engine.begin() as conn:
        conn.exec_driver_sql(sql)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
