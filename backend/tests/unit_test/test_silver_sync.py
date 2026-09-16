import pytest

from app.enums.employment_type import EmploymentType
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


@pytest.mark.parametrize("invalid", [False, 0, "", {}, "Remote", [""], [None]])
def test_invalid_locations_roll_back_all_updates(db_session, invalid):
    sync = SilverSync(db_session)
    sync.run([record()])
    db_session.commit()
    first = {**record(), "locations": ["New York"]}
    second = {**record(), "deduplication_key": "two", "locations": invalid}
    with pytest.raises((TypeError, ValueError)), db_session.begin():
        sync.run([first, second])
    job = db_session.query(JobPosting).one()
    assert sorted(location.name for location in job.locations) == ["Pittsburgh", "Remote"]
    assert db_session.query(Location).count() == 2


@pytest.mark.parametrize("empty", [None, [], ()])
def test_empty_locations_clear_associations(db_session, empty):
    sync = SilverSync(db_session)
    sync.run([record()])
    sync.run([{**record(), "locations": empty}])
    job = db_session.query(JobPosting).one()
    assert job.locations == []


def test_missing_locations_clear_associations(db_session):
    sync = SilverSync(db_session)
    row = record()
    sync.run([row])
    del row["locations"]
    sync.run([row])
    job = db_session.query(JobPosting).one()
    assert job.locations == []


def test_missing_employment_type_is_kept_raw_and_resolved_to_full_time(db_session):
    sync = SilverSync(db_session)
    sync.run([record(), {**record(), "deduplication_key": "two", "employment_type": "contract"}])
    db_session.commit()
    unstated = db_session.query(JobPosting).filter_by(source_key="silver:one").one()
    contract = db_session.query(JobPosting).filter_by(source_key="silver:two").one()
    assert unstated.employment_type is None
    assert unstated.employment_type_resolved == EmploymentType.FULL_TIME
    assert contract.employment_type == EmploymentType.CONTRACT
    assert contract.employment_type_resolved == EmploymentType.CONTRACT
    # The resolved value follows the raw one when a later snapshot changes it.
    sync.run([{**record(), "employment_type": "part-time"}])
    db_session.commit()
    db_session.refresh(unstated)
    assert unstated.employment_type == EmploymentType.PART_TIME
    assert unstated.employment_type_resolved == EmploymentType.PART_TIME
