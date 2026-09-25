from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.models import Category, JobPosting
from app.routers.job import router
from app.services.salary_sync import import_salary
from app.services.silver_sync import SilverSync


def test_synced_jobs_search_filter_pagination_and_detail(db_session):
    rows = [{"deduplication_key": str(i), "company_name": "Example AV", "job_name": f"Engineer {i}", "job_description": "Python autonomy", "locations": ["Remote", "Pittsburgh"], "skills": [{"name": "Python", "skill_type": "programming_language"}]} for i in range(3)]
    SilverSync(db_session).run(rows)
    # Sensing and Perception share the "Perception & Sensing" main_type
    # (see app/config/category_main_types.yaml), so both survive as
    # sub_types under one grouped `category` in the response.
    SilverSync(db_session).run([{**rows[0], "functional_area": ["Perception", "Sensing"]}])
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
        # None (not "") on a list item, distinguishing "not fetched for this
        # response" from a job whose description is genuinely blank.
        assert data["items"][0]["raw_description"] is None
        second = client.get("/jobs?page=2&page_size=2").json()
        assert len(second["items"]) == 1
        assert second["items"][0]["job_id"] not in {item["job_id"] for item in data["items"]}
        job = client.get("/jobs/" + data["items"][0]["job_id"]).json()
        assert job["locations"] == ["Pittsburgh", "Remote"]
        assert job["skills"] == ["Python"]
        assert job["source_url"] is None
        assert job["raw_description"] == "Python autonomy"
        assert client.get("/jobs?q=missing").json()["total"] == 0
        categorized = next(item for item in data["items"] + second["items"] if item["category"])
        category_id = categorized["category"]["sub_types"][0]["category_id"]
        filtered = client.get("/jobs", params={"category_id": category_id}).json()
        assert filtered["total"] == 1
        assert filtered["items"][0]["category"]["main_type"] == "Perception & Sensing"
        assert len(filtered["items"][0]["category"]["sub_types"]) == 2
        detail = client.get("/jobs/" + categorized["job_id"]).json()
        assert detail["category"] == categorized["category"]
        assert client.get("/jobs?category_id=bad").status_code == 422
        assert client.get("/jobs?page=0").status_code == 422
        assert client.get("/jobs/00000000-0000-0000-0000-000000000000").status_code == 404


def test_category_filter_never_matches_a_group_dropped_from_the_response(db_session):
    # Regression test: a job whose functional_area spans two main_types
    # (Perception & Sensing vs. System, 1 match each - a tie broken by
    # classifier order, so "Perception" wins since it's listed first) must
    # not still be filterable by the losing group's category_id. That would
    # let a user filter by Control and get back a job whose displayed
    # category never mentions Control at all.
    SilverSync(db_session).run([{
        "deduplication_key": "one", "company_name": "Example AV", "job_name": "Engineer", "job_description": "d",
        "functional_area": ["Perception", "Control"],
    }])
    db_session.commit()
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as client:
        job = client.get("/jobs").json()["items"][0]
        assert job["category"]["main_type"] == "Perception & Sensing"
        assert [s["sub_type"] for s in job["category"]["sub_types"]] == ["Perception"]

        perception_id = job["category"]["sub_types"][0]["category_id"]
        filtered = client.get("/jobs", params={"category_id": perception_id}).json()
        assert filtered["total"] == 1

        control_id = db_session.query(Category).filter_by(sub_type="Control").one().category_id
        filtered_out = client.get("/jobs", params={"category_id": str(control_id)}).json()
        assert filtered_out["total"] == 0


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

        # salary_disclosed keeps only ranges the employer published, in any
        # pay period - the levels.fyi estimate is excluded, unlike has_salary.
        disclosed = client.get("/jobs", params={"salary_disclosed": True}).json()
        assert {item["title"] for item in disclosed["items"]} == {"Yearly Low", "Yearly High", "Hourly"}

        undisclosed = client.get("/jobs", params={"salary_disclosed": False}).json()
        assert {item["title"] for item in undisclosed["items"]} == {"Estimated Only", "No Salary"}

        # The two flags combine: some salary info, but not a published range.
        estimate_only = client.get("/jobs", params={"has_salary": True, "salary_disclosed": False}).json()
        assert {item["title"] for item in estimate_only["items"]} == {"Estimated Only"}

        assert client.get("/jobs?min_salary=-1").status_code == 422


def test_sorting_by_posted_date_title_and_company(db_session):
    rows = [
        {"deduplication_key": "a", "company_name": "Zoox Systems", "job_name": "perception engineer", "job_description": "d"},
        {"deduplication_key": "b", "company_name": "Aurora Labs", "job_name": "Controls Engineer", "job_description": "d"},
        {"deduplication_key": "c", "company_name": "Motional AV", "job_name": "Mapping Engineer", "job_description": "d"},
        {"deduplication_key": "d", "company_name": "Waabi Inc", "job_name": "No Date Engineer", "job_description": "d"},
    ]
    SilverSync(db_session).run(rows)
    posted = {
        "perception engineer": datetime(2026, 9, 1, tzinfo=timezone.utc),
        "Controls Engineer": datetime(2026, 9, 10, tzinfo=timezone.utc),
        "Mapping Engineer": datetime(2026, 9, 5, tzinfo=timezone.utc),
    }
    for job in db_session.query(JobPosting):
        job.posted_date = posted.get(job.title)
    db_session.commit()

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as client:
        def titles(**params):
            return [item["title"] for item in client.get("/jobs", params=params).json()["items"]]

        # Default is unchanged: newest first, and the undated job goes last.
        assert titles() == ["Controls Engineer", "Mapping Engineer", "perception engineer", "No Date Engineer"]
        # Oldest first still keeps the undated job last rather than first.
        assert titles(sort="posted_date", direction="asc") == [
            "perception engineer", "Mapping Engineer", "Controls Engineer", "No Date Engineer",
        ]
        # Title sorting ignores case, so a lowercase title is not pushed to one end.
        assert titles(sort="title") == [
            "Controls Engineer", "Mapping Engineer", "No Date Engineer", "perception engineer",
        ]
        assert titles(sort="title", direction="desc") == [
            "perception engineer", "No Date Engineer", "Mapping Engineer", "Controls Engineer",
        ]
        # Company sorts on the company name, not on its UUID.
        assert titles(sort="company") == [
            "Controls Engineer", "Mapping Engineer", "No Date Engineer", "perception engineer",
        ]
        assert titles(sort="company", direction="desc") == [
            "perception engineer", "No Date Engineer", "Mapping Engineer", "Controls Engineer",
        ]
        # Paging a sorted list neither drops nor repeats a job.
        first = titles(sort="title", page=1, page_size=3)
        second = titles(sort="title", page=2, page_size=3)
        assert first + second == titles(sort="title")
        assert client.get("/jobs", params={"sort": "salary"}).status_code == 422
        assert client.get("/jobs", params={"sort": "title", "direction": "sideways"}).status_code == 422
