import pytest
from sqlalchemy.exc import IntegrityError

from app.models import JobPosting, Location
from app.services.salary_sync import import_salary
from app.services.silver_sync import SilverSync


def seed(db):
    SilverSync(db).run([{"deduplication_key": "one", "company_name": "AV", "job_name": "Engineer", "job_description": "Autonomy"}])
    db.commit()


def _row(**overrides):
    row = {
        "deduplication_key": "one",
        "salary_min": 150000,
        "salary_max": 200000,
        "salary_currency": "usd",
        "salary_period": "yearly",
        "salary_source": "api",
    }
    row.update(overrides)
    return row


def test_imports_salary_and_is_idempotent(db_session):
    seed(db_session)
    import_salary(db_session, [_row()])
    job = db_session.query(JobPosting).one()
    assert job.salary_min == 150000.0
    assert job.salary_max == 200000.0
    assert job.salary_currency == "USD"  # uppercased
    assert job.salary_period == "yearly"
    assert job.salary_source == "api"

    import_salary(db_session, [_row()])
    assert job.salary_min == 150000.0


def test_does_not_touch_locations_or_other_fields(db_session):
    """Regression test: salary import must only ever touch salary_* columns,
    same class of bug already caught once for skills."""
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

    import_salary(db_session, [_row()])

    assert [loc.name for loc in job.locations] == ["Berlin"]
    assert job.title == original_title
    assert db_session.query(Location).count() == 1


def test_missing_salary_min_key_is_a_noop(db_session):
    seed(db_session)
    result = import_salary(db_session, [{"deduplication_key": "one"}])
    job = db_session.query(JobPosting).one()
    assert job.salary_min is None
    assert result == {"read": 1, "updated": 0}


@pytest.mark.parametrize(
    "overrides",
    [
        {"salary_min": 0},
        {"salary_min": -100},
        {"salary_min": "150000"},
        {"salary_max": 100000, "salary_min": 150000},
        {"salary_currency": ""},
        {"salary_currency": None},
        {"salary_period": "biweekly"},
        {"salary_source": "made-up"},
    ],
)
def test_bad_batch_rolls_back(db_session, overrides):
    seed(db_session)
    with pytest.raises(ValueError), db_session.begin():
        import_salary(db_session, [_row(**overrides)])
    assert db_session.query(JobPosting).one().salary_min is None


def test_valid_salary_periods_and_sources_all_accepted(db_session):
    seed(db_session)
    for period in ("yearly", "monthly", "weekly", "daily", "hourly"):
        for source in ("api", "regex", "levels_fyi_average"):
            import_salary(db_session, [_row(salary_period=period, salary_source=source)])
            job = db_session.query(JobPosting).one()
            assert job.salary_period == period
            assert job.salary_source == source


def _average_row(**overrides):
    row = {
        "deduplication_key": "one",
        "salary_average": 251250,
        "salary_currency": "usd",
        "salary_period": "yearly",
        "salary_source": "levels_fyi_average",
    }
    row.update(overrides)
    return row


def test_salary_average_is_stored_separately_from_a_real_range(db_session):
    # Regression test: a single company-wide estimate (levels_fyi_average)
    # must not be duplicated into salary_min/salary_max, where it looks like
    # a suspiciously exact (min == max) real disclosed range.
    seed(db_session)
    import_salary(db_session, [_average_row()])
    job = db_session.query(JobPosting).one()
    assert job.salary_average == 251250.0
    assert job.salary_min is None
    assert job.salary_max is None
    assert job.salary_currency == "USD"
    assert job.salary_source == "levels_fyi_average"


def test_a_later_real_range_clears_a_previous_average_and_vice_versa(db_session):
    seed(db_session)
    import_salary(db_session, [_average_row()])
    job = db_session.query(JobPosting).one()
    assert job.salary_average == 251250.0

    import_salary(db_session, [_row()])  # a real range supersedes it
    assert job.salary_average is None
    assert job.salary_min == 150000.0

    import_salary(db_session, [_average_row()])  # and vice versa
    assert job.salary_min is None
    assert job.salary_average == 251250.0


def test_salary_average_and_range_together_is_rejected(db_session):
    seed(db_session)
    with pytest.raises(ValueError, match="mutually exclusive"), db_session.begin():
        import_salary(db_session, [_average_row(salary_min=150000, salary_max=200000)])
    assert db_session.query(JobPosting).one().salary_average is None


def test_salary_average_must_be_a_positive_number(db_session):
    seed(db_session)
    with pytest.raises(ValueError), db_session.begin():
        import_salary(db_session, [_average_row(salary_average=0)])
    assert db_session.query(JobPosting).one().salary_average is None


@pytest.mark.parametrize(
    "values",
    [
        {"salary_min": 0, "salary_max": 100},
        {"salary_min": 200, "salary_max": 100},
        {"salary_average": -1},
    ],
)
def test_database_rejects_invalid_salary_written_outside_sync(db_session, values):
    seed(db_session)
    job = db_session.query(JobPosting).one()
    for field, value in values.items():
        setattr(job, field, value)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
