import pytest

from app.services.category_sync import import_categories
from app.services.silver_sync import SilverSync


def seed(db, key="one"):
    SilverSync(db).run([{"deduplication_key": key, "company_name": "AV", "job_name": "Engineer", "job_description": "Autonomy"}])
    db.commit()


def test_clear_row_removes_a_jobs_existing_categories(db_session):
    seed(db_session)
    import_categories(db_session, [{"deduplication_key": "one", "functional_area": ["Infrastructure"]}])

    result = import_categories(db_session, [{"deduplication_key": "one", "functional_area": []}])

    from app.models import JobPosting

    job = db_session.query(JobPosting).filter_by(source_key="silver:one").one()
    assert job.categories == []
    assert result == {"read": 1, "updated": 1}


def test_clear_row_for_a_job_that_was_never_inserted_is_skipped_and_counted(db_session):
    seed(db_session)

    result = import_categories(
        db_session,
        [
            {"deduplication_key": "never-inserted", "functional_area": []},
            {"deduplication_key": "one", "functional_area": ["Perception"]},
        ],
    )

    assert result == {"read": 2, "updated": 1, "skipped_unmatched_clears": 1}


def test_a_row_that_assigns_categories_to_an_unknown_job_is_still_an_error(db_session):
    seed(db_session)

    with pytest.raises(ValueError, match="Row 1: No backend job matches"):
        import_categories(db_session, [{"deduplication_key": "never-inserted", "functional_area": ["Perception"]}])
