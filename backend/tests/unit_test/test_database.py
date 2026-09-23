"""Coverage for app/core/database.py's init_db/seed_db/get_db - previously
untested at all. init_db/seed_db are bound methods on the singleton
Database instance (`_db`), reading self.engine/self.Base rather than a
module global, so mocking them means patching those attributes on `_db`
itself - not on the module-level `engine`/`Base` aliases, which the bound
methods never look up. This mocks that engine rather than hitting a real
database (the same reason app.main's own tests patch init_db/seed_db
instead of calling them for real)."""

from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session


def test_get_db_yields_a_session_and_closes_it_after_use():
    from app.core.database import get_db

    generator = get_db()
    session = next(generator)

    assert isinstance(session, Session)
    with pytest.raises(StopIteration):
        next(generator)


@patch("app.core.database._db.Base")
def test_init_db_creates_all_tables_against_the_configured_engine(mock_base):
    from app.core.database import engine, init_db

    init_db()

    mock_base.metadata.create_all.assert_called_once_with(bind=engine)


@patch("app.core.database._db.engine")
def test_seed_db_executes_the_seed_companies_sql_file(mock_engine):
    from app.core.database import seed_db

    mock_connection = mock_engine.begin.return_value.__enter__.return_value

    # seed_db() resolves the SQL file relative to app/core/database.py, not
    # the process's working directory, so this reads the real seed file
    # rather than mocking open() with a path that would no longer match.
    seed_db()

    mock_connection.exec_driver_sql.assert_called_once()
    executed_sql = mock_connection.exec_driver_sql.call_args.args[0]
    assert "TRUNCATE TABLE company" in executed_sql


def test_database_refuses_a_second_instance():
    """The module already built one Database at import time; a second
    real instantiation would mean two connection pools racing against the
    database from the same process, so it must fail loudly instead of
    silently creating one."""
    from app.core.database import Database

    with pytest.raises(RuntimeError, match="already initialized"):
        Database()


def test_database_releases_its_claim_when_init_fails(monkeypatch):
    """__new__ claims cls._instance before __init__ runs, so a failed
    __init__ (e.g. DATABASE_URL unset) must release that claim - otherwise
    that one failed attempt permanently blocks every later, correctly
    configured Database() for the rest of the process."""
    from app.core.config import settings
    from app.core.database import Database

    original_instance = Database._instance
    Database._instance = None
    try:
        monkeypatch.setattr(settings, "database_url", None)
        with pytest.raises(RuntimeError, match="DATABASE_URL is not set"):
            Database()
        assert Database._instance is None

        monkeypatch.setattr(settings, "database_url", "sqlite:///:memory:")
        retried = Database()
        assert isinstance(retried, Database)
    finally:
        Database._instance = original_instance
