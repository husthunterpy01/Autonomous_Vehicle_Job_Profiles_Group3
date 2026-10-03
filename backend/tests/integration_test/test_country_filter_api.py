from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.routers.job import router
from app.services.silver_sync import SilverSync


def _client(db_session):
    rows = [
        ("us", "US job", ["Sunnyvale"]),
        ("both", "UK and US job", ["London; Sunnyvale"]),
        ("il", "Israel job", ["Tel Aviv, IL"]),
        ("remote", "Remote job", ["Remote"]),
        ("none", "No location job", []),
    ]
    SilverSync(db_session).run([
        {"deduplication_key": key, "company_name": "Example AV", "job_name": title,
         "job_description": "Autonomy", "locations": locations}
        for key, title, locations in rows
    ])
    db_session.commit()
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: db_session
    return TestClient(app)


def _titles(response):
    assert response.status_code == 200, response.text
    return sorted(item["title"] for item in response.json()["items"])


def test_country_filter_matches_every_location_of_a_job(db_session):
    with _client(db_session) as client:
        assert _titles(client.get("/jobs", params={"country": "United States"})) == ["UK and US job", "US job"]
        assert _titles(client.get("/jobs", params={"country": "united kingdom"})) == ["UK and US job"]
        assert _titles(client.get("/jobs", params={"country": "Israel"})) == ["Israel job"]
        assert _titles(client.get("/jobs", params={"country": "Canada"})) == []
        # Combines with the other filters.
        assert _titles(client.get("/jobs", params={"country": "United States", "q": "UK"})) == ["UK and US job"]


def test_empty_country_means_no_filter(db_session):
    with _client(db_session) as client:
        assert client.get("/jobs").json()["total"] == 5
        assert client.get("/jobs", params={"country": ""}).json()["total"] == 5
        assert client.get("/jobs", params={"country": "  "}).json()["total"] == 5


def test_unknown_country_is_a_400(db_session):
    with _client(db_session) as client:
        response = client.get("/jobs", params={"country": "Atlantis"})
        assert response.status_code == 400
        assert "Unknown country 'Atlantis'" in response.json()["detail"]
        assert client.get("/jobs", params={"country": "US"}).status_code == 400


def test_countries_endpoint_lists_countries_with_jobs(db_session):
    with _client(db_session) as client:
        response = client.get("/jobs/countries")
        assert response.status_code == 200
        assert response.json() == [
            {"country": "United States", "job_count": 2},
            {"country": "Israel", "job_count": 1},
            {"country": "United Kingdom", "job_count": 1},
        ]
        # /countries is not swallowed by /{job_id}, and job ids still resolve.
        assert client.get("/jobs/00000000-0000-0000-0000-000000000000").status_code == 404
