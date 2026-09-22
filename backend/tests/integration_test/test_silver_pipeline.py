from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from app.models import Category, JobPosting
from app.services.silver_pipeline import SilverPipeline
from app.services.silver_sync import SilverSync


def test_pipeline_preflight_commit_and_atomic_rollback(db_session):
    keys = ["f97c5d29941bfb1b2fdab0874906ab82", "b8a9f715dbb64fd5c56e7783c6820a61"]
    SilverSync(db_session).run([
        {"deduplication_key": key, "company_name": "Demo AV", "job_name": "Engineer", "job_description": "Autonomy"}
        for key in keys
    ])
    db_session.commit()
    pipeline = SilverPipeline(db_session.bind)
    records = [{"deduplication_key": key, "functional_area": "Perception"} for key in keys]
    assert pipeline.validate(records)["matched"] == 2
    with Session(db_session.bind) as check:
        assert check.query(Category).count() == 0
    assert pipeline.import_categories(records) == {"read": 2, "updated": 2}
    with pytest.raises(ValueError, match="Row 2"):
        pipeline.import_categories([
            {"deduplication_key": keys[0], "functional_area": "Controls"},
            {"deduplication_key": keys[1], "functional_area": None},
        ])
    with Session(db_session.bind) as check:
        assert check.query(Category).count() == 1
        assert all([c.sub_type for c in job.categories] == ["Perception"] for job in check.query(JobPosting))


def test_pipeline_requires_explicit_development_gate(db_session):
    with pytest.raises(ValueError, match="allow-unclassified"):
        SilverPipeline(db_session.bind).sync(None)


def test_pipeline_sync_streams_records_from_source_into_destination(db_session):
    # `source` stands in for a real Postgres engine holding
    # silver.cleaned_job_postings - only the connect()/execute()/mappings()
    # shape SilverPipeline.sync actually calls needs to match.
    source = MagicMock()
    row = {
        "deduplication_key": "one",
        "company_name": "AV Co",
        "job_name": "Engineer",
        "job_description": "Autonomy",
    }
    connection = source.connect.return_value.__enter__.return_value
    connection.execution_options.return_value.execute.return_value.mappings.return_value = [row]

    result = SilverPipeline(db_session.bind).sync(source, allow_unclassified=True)

    assert result["created"] == 1
    with Session(db_session.bind) as check:
        assert check.query(JobPosting).count() == 1
        assert check.query(JobPosting).one().title == "Engineer"


def test_pipeline_import_skills_delegates_to_skill_sync(db_session):
    SilverSync(db_session).run(
        [{"deduplication_key": "one", "company_name": "AV Co", "job_name": "Engineer", "job_description": "Autonomy"}]
    )
    db_session.commit()

    result = SilverPipeline(db_session.bind).import_skills(
        [{"deduplication_key": "one", "skills": [{"name": "ROS 2", "skill_type": "framework"}]}]
    )

    assert result["updated"] == 1
    with Session(db_session.bind) as check:
        job = check.query(JobPosting).one()
        assert [s.skill_name for s in job.skills] == ["ROS 2"]


def test_pipeline_import_salary_delegates_to_salary_sync(db_session):
    SilverSync(db_session).run(
        [{"deduplication_key": "one", "company_name": "AV Co", "job_name": "Engineer", "job_description": "Autonomy"}]
    )
    db_session.commit()

    result = SilverPipeline(db_session.bind).import_salary(
        [
            {
                "deduplication_key": "one",
                "salary_min": 150000,
                "salary_max": 200000,
                "salary_currency": "usd",
                "salary_period": "yearly",
                "salary_source": "api",
            }
        ]
    )

    assert result["updated"] == 1
    with Session(db_session.bind) as check:
        job = check.query(JobPosting).one()
        assert job.salary_min == 150000
