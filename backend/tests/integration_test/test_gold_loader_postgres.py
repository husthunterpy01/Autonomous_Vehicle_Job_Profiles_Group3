"""Opt-in DOC-13 check: load runs into a disposable copy of the gold schema."""

import os
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text

from app.services.gold_loader import GoldLoader, parse_run

pytestmark = pytest.mark.skipif(
    os.getenv("DOC13_TEST_POSTGRES") != "1",
    reason="Requires an explicitly configured PostgreSQL test database",
)

MIGRATION = Path(__file__).resolve().parents[2] / "app/sql/doc13_skill_trend_migration.sql"
KEY_A, KEY_B, KEY_C = "a" * 32, "b" * 32, "c" * 32


def utc(day, month=8):
    return datetime(2026, month, day, 12, tzinfo=timezone.utc)


def job(key, title, skills, categories=()):
    return {
        "deduplication_key": key,
        "job_name": title,
        "_classification": {
            "is_av_relevant": "True",
            "categories": list(categories),
            "skills": [{"name": name, "skill_type": "domain_concept"} for name in skills],
        },
    }


@pytest.fixture
def gold():
    database_url = os.getenv("DOC13_TEST_DATABASE_URL")
    if not database_url or not database_url.startswith("postgresql://"):
        pytest.fail("Set DOC13_TEST_DATABASE_URL to an isolated PostgreSQL test DB")
    schema = "gold_test_" + uuid4().hex
    engine = create_engine(database_url)
    migration = re.sub(r"\bgold\b", schema, MIGRATION.read_text(encoding="utf-8"))
    with engine.connect() as conn:
        conn.exec_driver_sql(migration)
        conn.commit()
    try:
        yield GoldLoader(engine, schema=schema), engine, schema
    finally:
        with engine.begin() as conn:
            conn.exec_driver_sql(f'DROP SCHEMA "{schema}" CASCADE')
        engine.dispose()


def load(loader, rows, scraped_at, **kwargs):
    jobs, _ = parse_run(rows)
    return loader.load(jobs, scraped_at=scraped_at, source="backfill", **kwargs)


def trend(engine, schema):
    with engine.connect() as conn:
        return [tuple(row) for row in conn.execute(text(
            f'SELECT month_key, skill_normalized_name, job_count, jobs_with_skills, rank '
            f'FROM "{schema}".skill_trend_monthly ORDER BY month_key, rank'
        ))]


def test_month_end_snapshot_idempotency_and_incomplete_runs(gold):
    loader, engine, schema = gold
    first = load(loader, [job(KEY_A, "Old title", ["LiDAR"]), job(KEY_B, "Planner", ["Motion Planning"])], utc(5))
    assert first["status"] == "loaded"
    assert (first["jobs"], first["skills"], first["facts"], first["month_key"]) == (2, 2, 2, 202608)

    month_end = [job(KEY_A, "Perception Engineer", ["LiDAR", "Camera"], ["Perception"]), job(KEY_C, "No skills", [])]
    result = load(loader, month_end, utc(31))
    assert (result["jobs"], result["jobs_without_skills"], result["facts"]) == (2, 1, 2)

    # Reloading a run changes nothing; a partial run registers without facts.
    assert load(loader, month_end, utc(31))["status"] == "already_loaded"
    partial = load(loader, [job(KEY_B, "Planner", ["Motion Planning"])], utc(30), completed=False)
    assert partial["status"] == "registered_incomplete"

    # August is the Aug 31 snapshot only: KEY_B (seen Aug 5 and in the partial run) is out.
    assert trend(engine, schema) == [
        (202608, "camera", 1, 1, 1),
        (202608, "lidar", 1, 1, 2),
    ]
    with engine.connect() as conn:
        assert conn.execute(text(
            f'SELECT title, main_type, first_seen_at, last_seen_at FROM "{schema}".dim_job '
            "WHERE deduplication_key = :k"), {"k": KEY_A}).one() == (
            "Perception Engineer", "Perception & Sensing", utc(5), utc(31))
        assert conn.execute(text(
            f'SELECT count(*) FROM "{schema}".fact_job_skill_month WHERE job_key = '
            f'(SELECT job_key FROM "{schema}".dim_job WHERE deduplication_key = :k)'), {"k": KEY_B}).scalar() == 1
        assert conn.execute(text(
            f'SELECT completed FROM "{schema}".scrape_run ORDER BY scraped_at')).scalars().all() == [True, False, True]


def test_out_of_order_backfill_keeps_the_newest_attributes(gold):
    loader, engine, schema = gold
    load(loader, [job(KEY_A, "September title", ["LiDAR"], ["Perception"])], utc(12, month=9))
    load(loader, [job(KEY_A, "August title", ["LiDAR", "Radar"])], utc(31))

    with engine.connect() as conn:
        assert conn.execute(text(
            f'SELECT title, main_type, first_seen_at, last_seen_at FROM "{schema}".dim_job')).one() == (
            "September title", "Perception & Sensing", utc(31), utc(12, month=9))
        assert conn.execute(text(f'SELECT count(*) FROM "{schema}".dim_skill')).scalar() == 2
    assert trend(engine, schema) == [
        (202608, "lidar", 1, 1, 1),
        (202608, "radar", 1, 1, 2),
        (202609, "lidar", 1, 1, 1),
    ]


def test_month_is_taken_in_utc(gold):
    loader, _, _ = gold
    # 1 Sep 02:00 in Perth is still 31 Aug in UTC.
    perth = datetime.fromisoformat("2026-09-01T02:00:00+08:00")
    assert load(loader, [job(KEY_A, "Engineer", ["LiDAR"])], perth)["month_key"] == 202608
