import pytest

from app.models import JobPosting, Location, Skill
from app.services.silver_sync import SilverSync
from app.services.skill_sync import import_skills


def seed(db):
    SilverSync(db).run([{"deduplication_key": "one", "company_name": "AV", "job_name": "Engineer", "job_description": "Autonomy"}])
    db.commit()


def test_imports_skills_and_is_idempotent(db_session):
    seed(db_session)
    row = {
        "deduplication_key": "one",
        "skills": [
            {"name": "ROS 2", "skill_type": "framework"},
            {"name": "Python", "skill_type": "programming_language"},
        ],
    }
    import_skills(db_session, [row])
    job = db_session.query(JobPosting).one()
    original = {s.skill_id for s in job.skills}
    assert {(s.skill_name, s.skill_type) for s in job.skills} == {
        ("ROS 2", "framework"),
        ("Python", "programming_language"),
    }

    import_skills(db_session, [row])
    assert {s.skill_id for s in job.skills} == original


def test_does_not_touch_locations_or_other_fields(db_session):
    """Regression test: a naive full SilverSync-style import would wipe
    locations when the handoff row (correctly) doesn't carry them - skill
    import must only ever touch skill/job_skill."""
    seed(db_session)
    SilverSync(db_session).run(
        [
            {
                "deduplication_key": "one",
                "company_name": "AV",
                "job_name": "Engineer",
                "job_description": "Autonomy",
                "locations": ["Berlin"],
            }
        ]
    )
    job = db_session.query(JobPosting).one()
    assert [loc.name for loc in job.locations] == ["Berlin"]
    original_title = job.title

    import_skills(db_session, [{"deduplication_key": "one", "skills": [{"name": "C++", "skill_type": "programming_language"}]}])

    assert [loc.name for loc in job.locations] == ["Berlin"]
    assert job.title == original_title
    assert db_session.query(Location).count() == 1


def test_deduplicates_reused_skill_across_jobs(db_session):
    seed(db_session)
    SilverSync(db_session).run(
        [{"deduplication_key": "two", "company_name": "AV", "job_name": "Other Engineer", "job_description": "Autonomy 2"}]
    )
    db_session.commit()

    import_skills(
        db_session,
        [
            {"deduplication_key": "one", "skills": [{"name": "python", "skill_type": "programming_language"}]},
            {"deduplication_key": "two", "skills": [{"name": "Python", "skill_type": "programming_language"}]},
        ],
    )
    assert db_session.query(Skill).count() == 1


def test_missing_skills_key_preserves_existing(db_session):
    seed(db_session)
    row = {"deduplication_key": "one", "skills": [{"name": "Python", "skill_type": "programming_language"}]}
    import_skills(db_session, [row])
    job = db_session.query(JobPosting).one()
    assert len(job.skills) == 1

    import_skills(db_session, [{"deduplication_key": "one"}])
    assert len(job.skills) == 1


def test_empty_array_clears_skills(db_session):
    seed(db_session)
    import_skills(
        db_session,
        [{"deduplication_key": "one", "skills": [{"name": "Python", "skill_type": "programming_language"}]}],
    )
    import_skills(db_session, [{"deduplication_key": "one", "skills": []}])
    assert db_session.query(JobPosting).one().skills == []


@pytest.mark.parametrize(
    "bad_skills",
    [
        "not-a-list",
        [{"name": "Python"}],
        [{"skill_type": "framework"}],
        [{"name": "", "skill_type": "framework"}],
        [{"name": "Python", "skill_type": "not-a-real-type"}],
    ],
)
def test_bad_batch_rolls_back(db_session, bad_skills):
    seed(db_session)
    with pytest.raises(ValueError), db_session.begin():
        import_skills(db_session, [{"deduplication_key": "one", "skills": bad_skills}])
    assert db_session.query(JobPosting).one().skills == []
    assert db_session.query(Skill).count() == 0
