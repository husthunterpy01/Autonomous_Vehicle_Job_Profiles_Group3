import pytest
from sqlalchemy import event

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


def test_main_type_assigned_from_static_mapping_on_create(db_session):
    # "Perception" -> "Perception & Sensing" comes from the real
    # backend/app/config/category_main_types.yaml, not from the record.
    # The main_type is deliberately not just "Perception" - a sub_type must
    # never share its own main_type's exact name.
    seed(db_session)
    import_categories(db_session, [{"deduplication_key": "one", "functional_area": "Perception"}])
    job = db_session.query(JobPosting).one()
    assert [(c.sub_type, c.main_type) for c in job.categories] == [("Perception", "Perception & Sensing")]


def test_main_type_self_heals_to_static_mapping_on_existing_category(db_session):
    seed(db_session)
    import_categories(db_session, [{"deduplication_key": "one", "functional_area": "Perception"}])
    category = db_session.query(Category).one()
    category.main_type = "some stale or hand-edited value"
    db_session.commit()

    import_categories(db_session, [{"deduplication_key": "one", "functional_area": "Perception"}])

    assert db_session.query(Category).one().main_type == "Perception & Sensing"


def test_unmapped_category_main_type_stays_none(db_session):
    seed(db_session)
    import_categories(db_session, [{"deduplication_key": "one", "functional_area": "Not A Real Category"}])
    job = db_session.query(JobPosting).one()
    assert job.categories[0].main_type is None


@pytest.mark.parametrize("bad_functional_area", [
    {"sub_type": "Perception", "main_type": "Perception"}, [{"sub_type": "Perception"}], [None], [3],
])
def test_object_labels_are_rejected(db_session, bad_functional_area):
    # functional_area is plain strings only - main_type per record was the
    # source of the last-writer-wins bug this replaced.
    seed(db_session)
    with pytest.raises(ValueError):
        import_categories(db_session, [{"deduplication_key": "one", "functional_area": bad_functional_area}])


def test_import_preloads_categories_in_one_query_instead_of_one_per_label_per_job(db_session):
    # Regression test: category lookups must not be one SELECT per label
    # per job - that was ~15-40k round-trips on a real import. 20 jobs x 5
    # of the 9 real categories each (100 label-instances) should still need
    # only ~1 SELECT for categories overall, not 100.
    categories = ["Perception", "Planning", "Mapping", "Control", "Sensing"]
    for i in range(20):
        SilverSync(db_session).run(
            [{"deduplication_key": f"job-{i}", "company_name": "AV", "job_name": "Engineer", "job_description": "Autonomy"}]
        )
    db_session.commit()

    rows = [{"deduplication_key": f"job-{i}", "functional_area": categories} for i in range(20)]

    select_count = 0

    def _count_selects(_conn, _cursor, statement, *_args, **_kwargs):
        nonlocal select_count
        if statement.strip().upper().startswith("SELECT"):
            select_count += 1

    event.listen(db_session.bind, "before_cursor_execute", _count_selects)
    try:
        import_categories(db_session, rows)
    finally:
        event.remove(db_session.bind, "before_cursor_execute", _count_selects)

    assert db_session.query(Category).count() == len(categories)
    # Well below the ~140 a one-SELECT-per-label-per-job pattern would need
    # for 100 label-instances, and doesn't grow with categories-per-job.
    assert select_count < 60


def test_only_the_dominant_main_type_group_is_actually_linked_to_the_job(db_session):
    # Regression test: a job whose functional_area spans two main_types
    # (Perception & Sensing has 1 match here, System has 1 - a tie broken
    # by classifier order, not alphabetically, so "Perception" wins since
    # it's listed first) must only link to that one group's Category rows
    # in job_category. Without this, the /jobs?category_id= filter (which
    # checks job_category directly) could match a category the response
    # never shows, since the response only ever displays the dominant group.
    seed(db_session)
    import_categories(db_session, [{"deduplication_key": "one", "functional_area": ["Perception", "Control"]}])

    job = db_session.query(JobPosting).one()

    assert [(c.sub_type, c.main_type) for c in job.categories] == [("Perception", "Perception & Sensing")]
    # The losing category's row still exists (other jobs may use it) - only
    # the *link* to this job is what gets dropped.
    assert db_session.query(Category).filter_by(sub_type="Control").one() is not None


def test_tie_break_follows_classifier_order_not_alphabetical(db_session):
    # Regression test: an earlier version sorted categories by
    # normalized_name before grouping, so a tie always fell to whichever
    # sub_type happened to sort first alphabetically - discarding real LLM
    # output for a naming coincidence (Mapping beating Perception because
    # "m" < "p", regardless of which the classifier actually listed first).
    # The tie must instead go to whichever group's sub_type functional_area
    # listed first - reversing the input order should reverse the winner.
    seed(db_session)
    import_categories(db_session, [{"deduplication_key": "one", "functional_area": ["Control", "Perception"]}])
    job = db_session.query(JobPosting).one()
    assert [c.sub_type for c in job.categories] == ["Control"]
