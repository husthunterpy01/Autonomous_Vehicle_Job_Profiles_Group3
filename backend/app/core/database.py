from collections.abc import Generator
from pathlib import Path
from time import monotonic

from sqlalchemy import create_engine, event, exc
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import settings

_SQL_DIR = Path(__file__).resolve().parent.parent / "sql"

# Hosted Postgres is ~250ms away; pinging on every checkout added a full
# round-trip to each API request. Recycle idle sockets and only ping when
# a connection has sat unused long enough that the pooler may have dropped it.
_IDLE_PING_AFTER_SECONDS = 30


class Database:
    """Owns the process's one SQLAlchemy engine/session factory/declarative
    base. A second instance would mean two connection pools racing against
    the database from the same process, so __new__ refuses to build one -
    use this module's engine/SessionLocal/Base/get_db instead of
    instantiating Database yourself."""

    _instance: "Database | None" = None

    def __new__(cls) -> "Database":  # noqa: PYI034 (Self needs Python 3.11+)
        if cls._instance is not None:
            raise RuntimeError(
                "Database is already initialized for this process; import "
                "app.core.database's engine/SessionLocal/Base/get_db instead "
                "of creating another instance"
            )
        cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        # __new__ already claimed cls._instance so a second, concurrent
        # Database() raises immediately - but if setup below fails, release
        # the claim so a later, correctly-configured retry isn't permanently
        # blocked by this failed attempt.
        try:
            self._configure()
        except Exception:
            Database._instance = None
            raise

    def _configure(self) -> None:
        url = settings.database_url
        if not url:
            # Without this, create_engine(None) fails with an opaque
            # "Expected string or URL object, got None" instead of naming
            # the actual missing setting.
            raise RuntimeError("DATABASE_URL is not set")

        self._is_postgres = url.startswith("postgres")

        engine_kwargs: dict = {}
        if self._is_postgres:
            engine_kwargs = {
                "pool_pre_ping": False,
                "pool_recycle": 300,
                "pool_size": 5,
                "max_overflow": 5,
                "pool_use_lifo": True,
            }
        self.engine = create_engine(url, **engine_kwargs)

        if self._is_postgres:
            self._register_idle_ping_listeners()

        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
        )
        self.Base = declarative_base()

    def _register_idle_ping_listeners(self) -> None:
        engine = self.engine

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

    def init_db(self) -> None:
        self.Base.metadata.create_all(bind=self.engine)

    def seed_db(self) -> None:
        """Inject company seed SQL on every server start."""
        sql = (_SQL_DIR / "seed_companies.sql").read_text(encoding="utf-8")
        with self.engine.begin() as conn:
            conn.exec_driver_sql(sql)

    def get_db(self) -> Generator[Session, None, None]:
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()


_db = Database()

engine = _db.engine
SessionLocal = _db.SessionLocal
Base = _db.Base
init_db = _db.init_db
seed_db = _db.seed_db
get_db = _db.get_db
