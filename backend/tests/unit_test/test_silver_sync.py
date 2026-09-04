import pytest

from app.models import Company, JobPosting, Location, Skill
from app.services.silver_sync import SilverSync


def record(**changes):
    return dict(deduplication_key="one", company_name="AV Company", job_name="Engineer", job_description="Build autonomy.", locations=["Pittsburgh", "Remote"], **changes)


def test_sync_is_idempotent_and_normalizes_locations(db_session):
    sync = SilverSync(db_session)
    assert sync.run([record()])["created"] == 1
    job = db_session.query(JobPosting).one()
    job_id = job.job_id
    row = record()
    row["locations"] = ["Remote", " remote "]
    row["job_name"] = "Senior Engineer"
    assert sync.run([row])["updated"] == 1
    assert job.job_id == job_id
    assert job.title == "Senior Engineer"
    assert len(job.locations) == 1
    assert db_session.query(Company).count() == 1
    assert db_session.query(Location).count() == 2
    assert job.source_url is None
    assert job.salary_average is None


def test_sync_preserves_metadata_and_skills_when_not_provided(db_session, company_factory):
    company = company_factory("AV Company")
    db_session.add(company)
    db_session.flush()
    website = company.website_url
    sync = SilverSync(db_session)
    row = record(skills=[{"name": "Python", "skill_type": "programming_language"}, {"name": "python", "skill_type": "programming_language"}])
    sync.run([row])
    sync.run([record()])
    assert db_session.query(Skill).count() == 1
    assert len(db_session.query(JobPosting).one().skills) == 1
    assert company.website_url == website
    sync.run([record(skills=[])])
    assert db_session.query(JobPosting).one().skills == []


def test_sync_failure_rolls_back_whole_batch(db_session):
    with pytest.raises(ValueError), db_session.begin():
        SilverSync(db_session).run([record(), record()])
    assert db_session.query(JobPosting).count() == 0
    assert db_session.query(Company).count() == 0
