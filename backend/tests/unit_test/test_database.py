"""Coverage for app/core/database.py's init_db/seed_db/get_db - previously
untested at all. init_db/seed_db touch the module-level `engine`, which is
bound to whatever settings.database_url points to, so these mock that engine
rather than hitting a real database (the same reason app.main's own tests
patch init_db/seed_db instead of calling them for real)."""

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


@patch("app.core.database.Base")
def test_init_db_creates_all_tables_against_the_configured_engine(mock_base):
    from app.core.database import engine, init_db

    init_db()

    mock_base.metadata.create_all.assert_called_once_with(bind=engine)


@patch("app.core.database.engine")
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
