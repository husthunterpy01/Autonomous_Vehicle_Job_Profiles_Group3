"""Resolve external handoff identities without relying on Bronze row numbers."""
from collections.abc import Mapping

from sqlalchemy.orm import Session

from app.models import JobPosting
from app.utils.validation import require_identifier


def resolve_job(db: Session, row: Mapping) -> JobPosting:
    """Prefer Silver identity; source_job_id + ats_name must resolve uniquely.

    External job_id is deliberately not interpreted: its meaning is not agreed.
    Supplied secondary identifiers must agree even when a Silver key is present.
    """
    key = row.get("deduplication_key")
    source_id = row.get("source_job_id")
    ats = row.get("ats_name")
    if key is not None:
        query = db.query(JobPosting).filter_by(
            source_key="silver:" + require_identifier(key, "deduplication_key")
        )
    else:
        if source_id is None or ats is None:
            raise ValueError("Provide deduplication_key or source_job_id together with ats_name; job_id/bronze_id are not join keys")
        query = db.query(JobPosting).filter_by(
            source_job_id=require_identifier(source_id, "source_job_id"),
            source_platform=require_identifier(ats, "ats_name"),
        )
    matches = query.limit(2).all()
    if not matches:
        raise ValueError("No backend job matches the supplied identity")
    if len(matches) > 1:
        raise ValueError("Ambiguous source identity; provide deduplication_key")
    job = matches[0]
    for field, value, stored in (
        ("source_job_id", source_id, job.source_job_id),
        ("ats_name", ats, job.source_platform),
    ):
        if value is not None and require_identifier(value, field) != stored:
            raise ValueError(f"{field} conflicts with the matched Silver identity")
    return job
