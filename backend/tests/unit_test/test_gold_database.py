"""DOC-13: the gold engine uses the site database's pool settings."""
import pytest

from app.core import gold_database


@pytest.fixture
def fresh_engine(monkeypatch):
    monkeypatch.setattr(gold_database, "_engine", None)
    monkeypatch.setattr(
        gold_database.settings, "gold_database_url", "postgresql://user:pw@localhost:5432/gold"
    )
    yield
    if gold_database._engine is not None:
        gold_database._engine.dispose()
    monkeypatch.setattr(gold_database, "_engine", None)


def test_no_ping_on_every_checkout_only_after_idle(fresh_engine):
    engine = gold_database.get_gold_engine()

    assert engine.pool._pre_ping is False
    # The idle-ping listeners from core/database.py are attached instead.
    assert len(engine.pool.dispatch.checkout) == 1
    assert len(engine.pool.dispatch.checkin) == 1
    assert gold_database.get_gold_engine() is engine


def test_one_connection_per_vercel_instance(fresh_engine, monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    engine = gold_database.get_gold_engine()
    assert (engine.pool.size(), engine.pool._max_overflow) == (1, 0)


def test_no_engine_without_a_gold_database(monkeypatch):
    monkeypatch.setattr(gold_database, "_engine", None)
    monkeypatch.setattr(gold_database.settings, "gold_database_url", None)
    assert gold_database.get_gold_engine() is None
