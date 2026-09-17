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
