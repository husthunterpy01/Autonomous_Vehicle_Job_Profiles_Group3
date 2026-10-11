from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.routers.job import router
from app.services.silver_sync import SilverSync

TITLES = [
    "Junior Perception Engineer",
    "Perception Engineer",
    "Planning Engineer",
    "Senior Planning Engineer",
    "Senior Controls Engineer",
    "Staff Software Engineer",
    "Engineering Manager",
]


def _client(db_session):
    SilverSync(db_session).run([
        {"deduplication_key": str(index), "company_name": "Example AV", "job_name": title,
         "job_description": "Autonomy", "locations": ["Remote"]}
        for index, title in enumerate(TITLES)
    ])
    db_session.commit()
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: db_session
    return TestClient(app)


def _titles(response):
    assert response.status_code == 200, response.text
    return sorted(item["title"] for item in response.json()["items"])


def test_seniority_filter_returns_only_that_level(db_session):
    with _client(db_session) as client:
        assert _titles(client.get("/jobs", params={"seniority_level": 3})) == [
            "Senior Controls Engineer",
            "Senior Planning Engineer",
        ]
        assert _titles(client.get("/jobs", params={"seniority_level": 1})) == ["Junior Perception Engineer"]
        assert _titles(client.get("/jobs", params={"seniority_level": 6})) == ["Engineering Manager"]
        assert _titles(client.get("/jobs", params={"seniority_level": 7})) == []


def test_unmarked_titles_are_mid_level(db_session):
    with _client(db_session) as client:
        assert _titles(client.get("/jobs", params={"seniority_level": 2})) == ["Perception Engineer", "Planning Engineer"]


def test_seniority_filter_combines_with_other_filters(db_session):
    with _client(db_session) as client:
        response = client.get("/jobs", params={"seniority_level": 3, "q": "Controls"})
        assert _titles(response) == ["Senior Controls Engineer"]
        assert response.json()["total"] == 1


def test_no_seniority_filter_returns_everything(db_session):
    with _client(db_session) as client:
        assert client.get("/jobs").json()["total"] == len(TITLES)


def test_invalid_seniority_level_is_rejected(db_session):
    with _client(db_session) as client:
        assert client.get("/jobs", params={"seniority_level": 10}).status_code == 422
        assert client.get("/jobs", params={"seniority_level": "senior"}).status_code == 422


def test_seniority_levels_endpoint_lists_levels_with_jobs(db_session):
    with _client(db_session) as client:
        response = client.get("/jobs/seniority-levels")
        assert response.status_code == 200
        assert response.json() == [
            {"seniority_level": 1, "job_count": 1},
            {"seniority_level": 2, "job_count": 2},
            {"seniority_level": 3, "job_count": 2},
            {"seniority_level": 4, "job_count": 1},
            {"seniority_level": 6, "job_count": 1},
        ]
        # Not swallowed by /{job_id}, and job ids still resolve.
        assert client.get("/jobs/00000000-0000-0000-0000-000000000000").status_code == 404


def test_seniority_levels_endpoint_skips_jobs_without_a_level(db_session):
    with _client(db_session) as client:
        from app.models import JobPosting

        job = db_session.query(JobPosting).filter_by(title="Engineering Manager").one()
        job.seniority_level = None
        db_session.commit()

        levels = [row["seniority_level"] for row in client.get("/jobs/seniority-levels").json()]
        assert 6 not in levels
