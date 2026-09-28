"""DOC-13: GET /api/v1/trends/skills against a stand-in gold.skill_trend_monthly."""
from collections.abc import Generator

import pytest
from sqlalchemy import Connection, create_engine, event, text
from sqlalchemy.pool import StaticPool

from app.core import gold_database
from app.core.gold_database import get_gold_connection
from app.main import app

AUG, SEP, OCT = 202608, 202609, 202610
SNAPSHOT = {AUG: "2026-08-31T14:17:29+00:00", SEP: "2026-09-12T05:46:21+00:00", OCT: "2026-10-30T02:00:00+00:00"}
LABEL = {AUG: "Aug 2026", SEP: "Sep 2026", OCT: "Oct 2026"}
# (month, display name, skill type, job count, rank, jobs with skills that month)
ROWS = [
    (AUG, "Python", "programming_language", 664, 1, 1074),
    (AUG, "C++", "programming_language", 625, 2, 1074),
    (AUG, "LiDAR", "domain_concept", 161, 3, 1074),
    (SEP, "Python", "programming_language", 806, 1, 1198),
    (SEP, "C++", "programming_language", 713, 2, 1198),
    (SEP, "LiDAR", "domain_concept", 206, 3, 1198),
    (SEP, "ROS 2", "framework", 12, 4, 1198),
    (OCT, "C++", "programming_language", 700, 1, 1200),
    (OCT, "Python", "programming_language", 690, 2, 1200),
    (OCT, "ROS 2", "framework", 300, 3, 1200),
    (OCT, "lidar", "domain_concept", 150, 4, 1200),
]


@pytest.fixture
def gold_rows():
    return list(ROWS)


@pytest.fixture
def trends_client(client, gold_rows) -> Generator:
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _attach_gold(dbapi_connection, _record):
        dbapi_connection.execute("ATTACH DATABASE ':memory:' AS gold")

    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE gold.skill_trend_monthly (month_key INTEGER, month_label TEXT, snapshot_at TEXT, "
            "skill_name TEXT, skill_normalized_name TEXT, skill_type TEXT, job_count INTEGER, "
            "jobs_with_skills INTEGER, rank INTEGER)"
        ))
        for month, name, skill_type, count, rank, total in gold_rows:
            conn.execute(text(
                "INSERT INTO gold.skill_trend_monthly VALUES (:m, :label, :at, :name, :norm, :type, :count, :total, :rank)"
            ), {"m": month, "label": LABEL[month], "at": SNAPSHOT[month], "name": name, "norm": name.lower(),
                "type": skill_type, "count": count, "total": total, "rank": rank})

    def override() -> Generator[Connection, None, None]:
        with engine.connect() as connection:
            yield connection

    app.dependency_overrides[get_gold_connection] = override
    yield client
    app.dependency_overrides.pop(get_gold_connection, None)
    engine.dispose()


def test_returns_latest_months_top_skills_with_their_rank_in_every_month(trends_client):
    response = trends_client.get("/api/v1/trends/skills", params={"limit": 3})

    assert response.status_code == 200
    body = response.json()
    assert [m["month_key"] for m in body["months"]] == [AUG, SEP, OCT]
    assert body["months"][0] == {
        "month_key": AUG, "label": "Aug 2026", "snapshot_at": "2026-08-31T14:17:29Z", "jobs_with_skills": 1074,
    }
    # Ordered by October's rank; ROS 2 enters in September, so August has no point for it.
    assert [(s["name"], s["skill_type"]) for s in body["skills"]] == [
        ("C++", "programming_language"), ("Python", "programming_language"), ("ROS 2", "framework"),
    ]
    assert body["skills"][2]["points"] == [
        {"month_key": SEP, "rank": 4, "job_count": 12},
        {"month_key": OCT, "rank": 3, "job_count": 300},
    ]
    assert [p["rank"] for p in body["skills"][1]["points"]] == [1, 1, 2]


def test_months_keeps_only_the_most_recent_ones(trends_client):
    body = trends_client.get("/api/v1/trends/skills", params={"limit": 4, "months": 2}).json()

    assert [m["month_key"] for m in body["months"]] == [SEP, OCT]
    assert all(p["month_key"] in (SEP, OCT) for s in body["skills"] for p in s["points"])
    # The latest display name wins ("lidar" in October, "LiDAR" before).
    assert body["skills"][3]["name"] == "lidar"


@pytest.mark.parametrize("gold_rows", [[]])
def test_an_empty_gold_mart_returns_no_months(trends_client):
    assert trends_client.get("/api/v1/trends/skills").json() == {"months": [], "skills": []}


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 31}, {"months": 0}, {"months": 37}])
def test_rejects_out_of_range_parameters(trends_client, params):
    assert trends_client.get("/api/v1/trends/skills", params=params).status_code == 422


def test_is_unavailable_when_no_gold_database_is_configured(client, monkeypatch):
    monkeypatch.setattr(gold_database.settings, "gold_database_url", None)
    response = client.get("/api/v1/trends/skills")
    assert response.status_code == 503
    assert response.json() == {"detail": "Skill trends are not configured"}
