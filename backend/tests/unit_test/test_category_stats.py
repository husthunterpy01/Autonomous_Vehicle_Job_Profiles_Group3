from app.services.category_stats import CategoryService
from app.services.category_sync import import_categories
from app.services.silver_sync import SilverSync


def seed(db, deduplication_key="one", job_name="Engineer"):
    SilverSync(db).run([{
        "deduplication_key": deduplication_key,
        "company_name": "AV",
        "job_name": job_name,
        "job_description": "Autonomy",
    }])
    db.commit()


def test_returns_empty_list_when_no_categories_exist(db_session):
    seed(db_session)

    assert CategoryService(db_session).get_category_stat_per_job() == []


def test_counts_each_sub_type_once_per_job_and_reports_its_main_type(db_session):
    seed(db_session)
    import_categories(db_session, [{"deduplication_key": "one", "functional_area": ["Perception", "Sensing"]}])

    stats = {s.sub_type: (s.main_type, s.job_count) for s in CategoryService(db_session).get_category_stat_per_job()}

    # Perception and Sensing share the "Perception & Sensing" main_type
    # (see app/config/category_main_types.yaml).
    assert stats == {
        "Perception": ("Perception & Sensing", 1),
        "Sensing": ("Perception & Sensing", 1),
    }


def test_counts_a_sub_type_shared_across_multiple_jobs(db_session):
    seed(db_session, "one", "Engineer One")
    seed(db_session, "two", "Engineer Two")
    import_categories(db_session, [
        {"deduplication_key": "one", "functional_area": ["Perception"]},
        {"deduplication_key": "two", "functional_area": ["Perception"]},
    ])

    stats = CategoryService(db_session).get_category_stat_per_job()

    assert len(stats) == 1
    assert stats[0].sub_type == "Perception"
    assert stats[0].job_count == 2


def test_job_with_no_categories_does_not_affect_other_counts(db_session):
    seed(db_session, "one", "Engineer One")
    seed(db_session, "two", "Engineer Two")
    import_categories(db_session, [
        {"deduplication_key": "one", "functional_area": ["Perception"]},
        {"deduplication_key": "two"},
    ])

    stats = CategoryService(db_session).get_category_stat_per_job()

    assert len(stats) == 1
    assert stats[0].job_count == 1


def test_unmapped_sub_type_reports_null_main_type(db_session):
    seed(db_session)
    import_categories(db_session, [{"deduplication_key": "one", "functional_area": ["Not A Real Category"]}])

    stats = CategoryService(db_session).get_category_stat_per_job()

    assert len(stats) == 1
    assert stats[0].sub_type == "Not A Real Category"
    assert stats[0].main_type is None
