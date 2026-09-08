from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.routers.job import router
from app.services.silver_sync import SilverSync


def test_synced_jobs_search_filter_pagination_and_detail(db_session):
    rows = [{"deduplication_key": str(i), "company_name": "Example AV", "job_name": f"Engineer {i}", "job_description": "Python autonomy", "locations": ["Remote", "Pittsburgh"], "skills": [{"name": "Python", "skill_type": "programming_language"}]} for i in range(3)]
    SilverSync(db_session).run(rows)
    SilverSync(db_session).run([{**rows[0], "functional_area": ["Perception", "Controls"]}])
    db_session.commit()
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as client:
        response = client.get("/jobs", params={"q": "Engineer", "location": "Remote", "skill": "Python", "page_size": 2})
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert data["total_pages"] == 2
        assert len(data["items"]) == 2
        second = client.get("/jobs?page=2&page_size=2").json()
        assert len(second["items"]) == 1
        assert second["items"][0]["job_id"] not in {item["job_id"] for item in data["items"]}
        job = client.get("/jobs/" + data["items"][0]["job_id"]).json()
        assert job["locations"] == ["Pittsburgh", "Remote"]
        assert job["skills"] == ["Python"]
        assert job["source_url"] is None
        assert client.get("/jobs?q=missing").json()["total"] == 0
        categorized = next(item for item in data["items"] + second["items"] if item["categories"])
        category_id = categorized["categories"][0]["category_id"]
        filtered = client.get("/jobs", params={"category_id": category_id}).json()
        assert filtered["total"] == 1
        assert len(filtered["items"][0]["categories"]) == 2
        detail = client.get("/jobs/" + categorized["job_id"]).json()
        assert detail["categories"] == categorized["categories"]
        assert client.get("/jobs?category_id=bad").status_code == 422
        assert client.get("/jobs?page=0").status_code == 422
        assert client.get("/jobs/00000000-0000-0000-0000-000000000000").status_code == 404
