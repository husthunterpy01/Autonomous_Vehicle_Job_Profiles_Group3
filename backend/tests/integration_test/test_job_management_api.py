from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import event

from app.core.config import settings
from app.core.database import get_db
from app.models import Category, JobPosting, Location, Skill
from app.routers.job import router


def _client(db_session):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: db_session
    return TestClient(app)


def test_create_job_links_taxonomy_and_is_immediately_retrievable(
    db_session, company_factory, monkeypatch
):
    monkeypatch.setattr(settings, "job_write_api_key", "test-write-key")
    company = company_factory("Create Job AV")
    location = Location(name="Perth, Australia", normalized_name="perth, australia")
    skill = Skill(
        skill_name="Python", normalized_name="python", skill_type="programming_language"
    )
    category = Category(
        main_type="Software",
        sub_type="Backend",
        normalized_name="backend",
        taxonomy_version=1,
    )
    db_session.add_all([company, location, skill, category])
    db_session.commit()

    payload = {
        "source_key": "create-job-av-42",
        "company_id": str(company.company_id),
        "title": "AV Backend Engineer",
        "description": "Build APIs for autonomous vehicle data.",
        "requirements": "Python and PostgreSQL",
        "department": "Engineering",
        "employment_type": 1,
        "seniority_level": 3,
        "posted_date": "2026-09-21T08:00:00Z",
        "source_platform": "Greenhouse",
        "source_job_id": "42",
        "source_url": "https://example.com/jobs/42",
        "salary_min": 120000,
        "salary_max": 160000,
        "salary_currency": "aud",
        "salary_period": "yearly",
        "salary_source": "api",
        "locations": ["Remote"],
        "skills": [{"name": "PostgreSQL", "skill_type": "tool"}],
        "categories": [
            {
                "main_type": "Software",
                "sub_type": "API Platform",
                "taxonomy_version": 1,
            }
        ],
        "location_ids": [str(location.location_id)],
        "skill_ids": [str(skill.skill_id)],
        "category_ids": [str(category.category_id)],
    }

    with _client(db_session) as client:
        assert client.post("/jobs", json=payload).status_code == 401
        created = client.post(
            "/jobs", json=payload, headers={"X-Job-Write-Key": "test-write-key"}
        )
        assert created.status_code == 201
        body = created.json()
        assert body["company_name"] == "Create Job AV"
        assert body["requirements"] == "Python and PostgreSQL"
        assert body["locations"] == ["Perth, Australia", "Remote"]
        assert body["skills"] == ["PostgreSQL", "Python"]
        assert {
            item["sub_type"] for item in body["category"]["sub_types"]
        } == {"Backend", "API Platform"}
        assert body["salary_currency"] == "AUD"
        assert db_session.query(Location).filter_by(normalized_name="remote").count() == 1
        assert (
            db_session.query(Skill)
            .filter_by(normalized_name="postgresql", skill_type="tool")
            .count()
            == 1
        )

        detail = client.get(f"/jobs/{body['job_id']}")
        assert detail.status_code == 200
        assert detail.json() == body

        filtered = client.get(
            "/jobs",
            params={
                "company_id": str(company.company_id),
                "location": "Perth",
                "skill": "Python",
                "category_id": str(category.category_id),
            },
        ).json()
        assert filtered["total"] == 1
        assert filtered["items"][0]["job_id"] == body["job_id"]

        duplicate = client.post(
            "/jobs", json=payload, headers={"X-Job-Write-Key": "test-write-key"}
        )
        assert duplicate.status_code == 409
        assert "source_key" in duplicate.json()["detail"]


def test_non_ascii_write_key_is_rejected_without_server_error(
    db_session, monkeypatch
):
    monkeypatch.setattr(settings, "job_write_api_key", "test-write-key")
    payload = {
        "source_key": "unicode-key-test",
        "company_id": str(uuid4()),
        "title": "Engineer",
        "description": "Description",
    }

    with _client(db_session) as client:
        response = client.post(
            "/jobs",
            json=payload,
            headers={b"X-Job-Write-Key": "café".encode()},
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing job write API key"


def test_create_job_reports_missing_relations_and_mixed_categories(
    db_session, company_factory, monkeypatch
):
    monkeypatch.setattr(settings, "job_write_api_key", "test-write-key")
    company = company_factory("Validation AV")
    categories = [
        Category(
            main_type="Software",
            sub_type="Backend",
            normalized_name="backend",
            taxonomy_version=1,
        ),
        Category(
            main_type="Hardware",
            sub_type="Sensors",
            normalized_name="sensors",
            taxonomy_version=1,
        ),
    ]
    db_session.add_all([company, *categories])
    db_session.commit()
    headers = {"X-Job-Write-Key": "test-write-key"}
    base = {
        "source_key": "validation-job",
        "company_id": str(company.company_id),
        "title": "Engineer",
        "description": "Description",
    }

    with _client(db_session) as client:
        missing_company = client.post(
            "/jobs", json={**base, "company_id": str(uuid4())}, headers=headers
        )
        assert missing_company.status_code == 404
        assert "Company not found" in missing_company.json()["detail"]

        missing_skill = client.post(
            "/jobs", json={**base, "skill_ids": [str(uuid4())]}, headers=headers
        )
        assert missing_skill.status_code == 404
        assert "Unknown skill IDs" in missing_skill.json()["detail"]

        mixed = client.post(
            "/jobs",
            json={
                **base,
                "category_ids": [str(category.category_id) for category in categories],
            },
            headers=headers,
        )
        assert mixed.status_code == 400
        assert "one taxonomy version" in mixed.json()["detail"]


def test_list_query_count_is_constant_as_page_size_grows(db_session, seeded_companies):
    """Protect the normal-load list endpoint from latency and N+1 regressions."""
    company = seeded_companies["alpha"]
    db_session.add_all(
        [
            JobPosting(
                name=f"performance-job-{index}",
                title=f"Performance Engineer {index}",
                raw_description="AV platform engineering",
                company_id=company.company_id,
            )
            for index in range(100)
        ]
    )
    db_session.commit()
    statements = []

    def record_statement(_connection, _cursor, statement, _parameters, _context, _many):
        statements.append(statement)

    event.listen(db_session.bind, "before_cursor_execute", record_statement)
    try:
        with _client(db_session) as client:
            started = perf_counter()
            response = client.get("/jobs", params={"page_size": 100})
            elapsed = perf_counter() - started
            assert response.status_code == 200
            assert response.json()["total"] == 103
    finally:
        event.remove(db_session.bind, "before_cursor_execute", record_statement)

    selects = [
        statement
        for statement in statements
        if statement.lstrip().upper().startswith("SELECT")
    ]
    assert len(selects) <= 3
    assert elapsed < 2.0
