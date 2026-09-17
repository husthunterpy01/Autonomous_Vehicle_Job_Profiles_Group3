import pytest
from sqlalchemy import event

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


def test_import_preloads_skills_in_one_query_instead_of_one_per_label_per_job(db_session):
    # Regression test: skill lookups must not be one SELECT per label per
    # job - that was ~15-40k round-trips on a real import. 20 jobs x 5
    # skills each (100 label-instances) should still need only ~1 SELECT for
    # skills overall, not 100 - a one-SELECT-per-label-per-job pattern would
    # need ~140 total (100 skill lookups + resolve_job + the ORM's own
    # lazy-load of each job's existing skills collection before replacing
    # it); the fix should stay close to the ~41 that resolve_job/lazy-load
    # alone cost, regardless of how many skills each job has.
    skill_names = ["Python", "ROS 2", "C++", "Docker", "PyTorch"]
    for i in range(20):
        SilverSync(db_session).run(
            [{"deduplication_key": f"job-{i}", "company_name": "AV", "job_name": "Engineer", "job_description": "Autonomy"}]
        )
    db_session.commit()

    rows = [
        {
            "deduplication_key": f"job-{i}",
            "skills": [{"name": name, "skill_type": "framework"} for name in skill_names],
        }
        for i in range(20)
    ]

    select_count = 0

    def _count_selects(_conn, _cursor, statement, *_args, **_kwargs):
        nonlocal select_count
        if statement.strip().upper().startswith("SELECT"):
            select_count += 1

    event.listen(db_session.bind, "before_cursor_execute", _count_selects)
    try:
        import_skills(db_session, rows)
    finally:
        event.remove(db_session.bind, "before_cursor_execute", _count_selects)

    assert db_session.query(Skill).count() == len(skill_names)
    # Well below the ~140 a one-SELECT-per-label-per-job pattern would need
    # for 100 label-instances, and doesn't grow with skills-per-job.
    assert select_count < 60


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
