from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.models import JobPosting
from app.routers.job import router
from app.services.salary_sync import import_salary
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


def test_salary_filters_and_response_fields(db_session):
    rows = [
        {"deduplication_key": "yearly-1", "company_name": "Example AV", "job_name": "Yearly Low", "job_description": "d"},
        {"deduplication_key": "yearly-2", "company_name": "Example AV", "job_name": "Yearly High", "job_description": "d"},
        {"deduplication_key": "hourly-1", "company_name": "Example AV", "job_name": "Hourly", "job_description": "d"},
        {"deduplication_key": "no-salary", "company_name": "Example AV", "job_name": "No Salary", "job_description": "d"},
        {"deduplication_key": "estimate-1", "company_name": "Example AV", "job_name": "Estimated Only", "job_description": "d"},
    ]
    SilverSync(db_session).run(rows)
    db_session.commit()
    import_salary(
        db_session,
        [
            {"deduplication_key": "yearly-1", "salary_min": 80000, "salary_max": 100000, "salary_currency": "usd", "salary_period": "yearly", "salary_source": "api"},
            {"deduplication_key": "yearly-2", "salary_min": 150000, "salary_max": 200000, "salary_currency": "usd", "salary_period": "yearly", "salary_source": "regex"},
            {"deduplication_key": "hourly-1", "salary_min": 20, "salary_max": 40, "salary_currency": "usd", "salary_period": "hourly", "salary_source": "regex"},
            {"deduplication_key": "estimate-1", "salary_average": 251250, "salary_currency": "usd", "salary_period": "yearly", "salary_source": "levels_fyi_average"},
        ],
    )
    db_session.commit()

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as client:
        yearly_high = client.get("/jobs/" + str(db_session.query(JobPosting).filter_by(title="Yearly High").one().job_id)).json()
        assert yearly_high["salary_min"] == 150000.0
        assert yearly_high["salary_max"] == 200000.0
        assert yearly_high["salary_currency"] == "USD"
        assert yearly_high["salary_period"] == "yearly"
        assert yearly_high["salary_source"] == "regex"

        no_salary = client.get("/jobs/" + str(db_session.query(JobPosting).filter_by(title="No Salary").one().job_id)).json()
        assert no_salary["salary_min"] is None
        assert no_salary["salary_source"] is None

        # A levels.fyi company-wide estimate has no real range - it's on
        # salary_average, with salary_min/salary_max left null, not
        # duplicated into a suspiciously exact min == max range.
        estimated = client.get("/jobs/" + str(db_session.query(JobPosting).filter_by(title="Estimated Only").one().job_id)).json()
        assert estimated["salary_average"] == 251250.0
        assert estimated["salary_min"] is None
        assert estimated["salary_max"] is None
        assert estimated["salary_source"] == "levels_fyi_average"

        # min_salary/max_salary require salary_period: comparing raw
        # magnitudes across periods/currencies is meaningless (a $30/hour
        # rate vs a $150,000/year salary), so the API rejects the ambiguous
        # combination instead of silently mixing them.
        assert client.get("/jobs", params={"min_salary": 120000}).status_code == 422
        assert client.get("/jobs", params={"max_salary": 120000}).status_code == 422

        # With salary_period given, the magnitude comparison stays within
        # that one bucket - overlap semantics: job's range must reach the
        # floor and/or stay under the ceiling, among yearly rows only. The
        # "Estimated Only" job (salary_average, no real range) never
        # qualifies for either, even though its estimate is >120k - it has
        # no salary_min/salary_max to compare at all.
        above_120k = client.get("/jobs", params={"min_salary": 120000, "salary_period": "yearly"}).json()
        assert {item["title"] for item in above_120k["items"]} == {"Yearly High"}

        under_120k = client.get("/jobs", params={"max_salary": 120000, "salary_period": "yearly"}).json()
        assert {item["title"] for item in under_120k["items"]} == {"Yearly Low"}

        # salary_period alone doesn't distinguish a real range from an
        # estimate - "Estimated Only" is genuinely period="yearly" too, it
        # just has no salary_min/salary_max to also satisfy a magnitude filter.
        yearly_only = client.get("/jobs", params={"salary_period": "yearly"}).json()
        assert {item["title"] for item in yearly_only["items"]} == {"Yearly Low", "Yearly High", "Estimated Only"}

        assert client.get("/jobs", params={"salary_period": "annual"}).status_code == 422

        # has_salary counts an estimate-only job too - it does have *some*
        # salary info, just not a real disclosed range.
        has_salary = client.get("/jobs", params={"has_salary": True}).json()
        assert has_salary["total"] == 4
        assert {"No Salary"}.isdisjoint({item["title"] for item in has_salary["items"]})
        assert "Estimated Only" in {item["title"] for item in has_salary["items"]}

        no_salary_only = client.get("/jobs", params={"has_salary": False}).json()
        assert {item["title"] for item in no_salary_only["items"]} == {"No Salary"}

        assert client.get("/jobs?min_salary=-1").status_code == 422


def test_employment_type_serves_resolved_value(db_session):
    rows = [
        {"deduplication_key": "unstated", "company_name": "Example AV", "job_name": "Unstated", "job_description": "d"},
        {"deduplication_key": "contract", "company_name": "Example AV", "job_name": "Contract", "job_description": "d", "employment_type": "contract"},
    ]
    SilverSync(db_session).run(rows)
    db_session.commit()
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as client:
        unstated = db_session.query(JobPosting).filter_by(title="Unstated").one()
        assert unstated.employment_type is None
        # The raw null stays in the database; the API only exposes the
        # resolved value, under the existing field name.
        detail = client.get("/jobs/" + str(unstated.job_id)).json()
        assert detail["employment_type"] == 1
        assert "employment_type_resolved" not in detail
        full_time = client.get("/jobs", params={"employment_type": 1}).json()
        assert {item["title"] for item in full_time["items"]} == {"Unstated"}
        contract = client.get("/jobs", params={"employment_type": 3}).json()
        assert {item["title"] for item in contract["items"]} == {"Contract"}
