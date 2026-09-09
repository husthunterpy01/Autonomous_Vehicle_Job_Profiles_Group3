import pytest

from app.models import JobPosting
from app.services.handoff import validate_records
from app.services.job_identity import resolve_job
from app.services.silver_sync import SilverSync


def seed(db, key="f97c5d29941bfb1b2fdab0874906ab82", **values):
    row = {"deduplication_key": key, "company_name": "AV", "job_name": "Engineer",
               "job_description": "Autonomy", "source_job_id": "42", "ats_name": "greenhouse", "bronze_id": 1}
    row.update(values)
    SilverSync(db).run([row])
    return resolve_job(db, {"deduplication_key": key})


def test_bronze_changes_preserve_identity_without_source_id(db_session):
    job_id = seed(db_session, source_job_id=None).job_id
    assert seed(db_session, source_job_id=None, bronze_id=999).job_id == job_id
    assert db_session.query(JobPosting).count() == 1


def test_source_id_scoped_by_ats(db_session):
    first = seed(db_session)
    second = seed(db_session, "b8a9f715dbb64fd5c56e7783c6820a61", ats_name="lever")
    assert resolve_job(db_session, {"source_job_id": "42", "ats_name": "greenhouse"}) == first
    assert resolve_job(db_session, {"source_job_id": "42", "ats_name": "lever"}) == second


def test_same_ats_collisions_require_silver_key(db_session):
    seed(db_session)
    second = seed(db_session, "b8a9f715dbb64fd5c56e7783c6820a61", company_name="Other AV")
    with pytest.raises(ValueError, match="Ambiguous"):
        resolve_job(db_session, {"source_job_id": "42", "ats_name": "greenhouse"})
    assert resolve_job(db_session, {"deduplication_key": "b8a9f715dbb64fd5c56e7783c6820a61"}) == second


@pytest.mark.parametrize("identity", [
    {"job_id": "1"}, {"bronze_id": 1}, {"source_job_id": "42"},
    {"deduplication_key": ""}, {"deduplication_key": "00000000000000000000000000000000"},
    {"deduplication_key": "f97c5d29941bfb1b2fdab0874906ab82", "source_job_id": "wrong"},
    {"deduplication_key": "f97c5d29941bfb1b2fdab0874906ab82", "ats_name": "lever"},
    {"deduplication_key": "00000000000000000000000000000000", "source_job_id": "42", "ats_name": "greenhouse"},
])
def test_unsafe_identity_rejected(db_session, identity):
    seed(db_session)
    with pytest.raises(ValueError):
        resolve_job(db_session, identity)


def test_preflight_reports_importable_category_and_makes_no_changes(db_session):
    job = seed(db_session)
    db_session.commit()
    report = validate_records(db_session, [{"deduplication_key": "f97c5d29941bfb1b2fdab0874906ab82", "functional_area": "Perception"}])
    assert report["writes"] == 0
    assert report["items"][0]["backend_job_id"] == str(job.job_id)
    assert report["items"][0]["category_status"] == "ready_to_import"
    assert not db_session.dirty and not db_session.new and not db_session.deleted
    with pytest.raises(ValueError, match="Row 2.*same backend job"):
        validate_records(db_session, [{"deduplication_key": "f97c5d29941bfb1b2fdab0874906ab82"}] * 2)


@pytest.mark.parametrize("records", [{}, [None]])
def test_invalid_handoff_shape(db_session, records):
    with pytest.raises((TypeError, ValueError)):
        validate_records(db_session, records)
