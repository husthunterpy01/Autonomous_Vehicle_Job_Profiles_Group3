import pytest

from app.models import Category, JobPosting
from app.services.category_sync import import_categories
from app.services.silver_sync import SilverSync


def seed(db):
    SilverSync(db).run([{"deduplication_key": "one", "company_name": "AV", "job_name": "Engineer", "job_description": "Autonomy"}])
    db.commit()


def test_labels_normalize_preserve_clear_and_version(db_session):
    seed(db_session)
    row = {"deduplication_key": "one", "functional_area": ["  Computer   Vision ", "computer vision", "ＭＬ"]}
    import_categories(db_session, [row])
    job = db_session.query(JobPosting).one()
    original = {c.category_id for c in job.categories}
    import_categories(db_session, [row])
    assert {c.category_id for c in job.categories} == original
    assert {c.normalized_name for c in job.categories} == {"computer vision", "ml"}
    assert all(c.main_type is None for c in job.categories)
    import_categories(db_session, [{"deduplication_key": "one"}])
    assert len(job.categories) == 2
    import_categories(db_session, [{**row, "taxonomy_version": 2}])
    assert all(c.taxonomy_version == 2 for c in job.categories)
    assert db_session.query(Category).count() == 4
    import_categories(db_session, [{**row, "functional_area": []}])
    assert job.categories == []


@pytest.mark.parametrize("changes", [
    {"functional_area": None}, {"functional_area": " "}, {"functional_area": [3]},
    {"taxonomy_version": True}, {"taxonomy_version": 0},
])
def test_bad_batch_rolls_back_categories(db_session, changes):
    seed(db_session)
    with pytest.raises(ValueError), db_session.begin():
        import_categories(db_session, [{"deduplication_key": "one", "functional_area": "Perception"}])
        import_categories(db_session, [{"deduplication_key": "one", "functional_area": "Controls", **changes}])
    assert db_session.query(Category).count() == 0
    assert db_session.query(JobPosting).one().categories == []


def test_silver_inline_categories_and_missing_preserves(db_session):
    row = {"deduplication_key": "one", "company_name": "AV", "job_name": "Engineer", "job_description": "Autonomy"}
    SilverSync(db_session).run([{**row, "functional_area": "Planning/Controls"}])
    SilverSync(db_session).run([row])
    assert [c.sub_type for c in db_session.query(JobPosting).one().categories] == ["Planning/Controls"]
