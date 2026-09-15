"""Normalize Silver rows into backend tables within the caller's transaction."""
from collections.abc import Iterable, Mapping
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Company, JobPosting, Location
from app.services.category_sync import _collect_category_keys, _preload_categories, sync_categories
from app.services.skill_sync import _collect_skill_keys, _preload_skills, sync_skills
from app.utils.normalization import normalized

EMPLOYMENT_TYPES = {"full-time": 1, "part-time": 2, "contract": 3, "temporary": 4, "internship": 5}


class SilverSync:
    def __init__(self, db: Session):
        self.db = db

    def run(self, records: Iterable[Mapping]) -> dict[str, int]:
        # Materialized once so both the preload scan below and the main loop
        # can see every row - the caller may pass a one-shot streaming
        # cursor (see SilverPipeline.sync). Trading that streaming memory
        # profile for one preload query instead of one SELECT per label per
        # job is worth it at the scale this runs at (~15-40k round-trips
        # otherwise on a full import).
        records = list(records)
        counts = {"read": 0, "created": 0, "updated": 0}
        category_cache = _preload_categories(self.db, _collect_category_keys(records))
        skill_cache = _preload_skills(self.db, _collect_skill_keys(records))
        seen = set()
        for row in records:
            counts["read"] += 1
            key = row.get("deduplication_key")
            if not isinstance(key, str) or not key.strip():
                raise ValueError("Every Silver row requires a deduplication_key")
            if key in seen:
                raise ValueError("Duplicate Silver source key in input")
            seen.add(key)
            for field in ("company_name", "job_name", "job_description"):
                if not isinstance(row.get(field), str) or not row[field].strip():
                    raise ValueError(f"Silver row requires {field}")
            company_name = " ".join(row["company_name"].split())
            company = self.db.query(Company).filter(func.lower(Company.name) == company_name.lower()).one_or_none()
            if company is None:
                company = Company(name=company_name, datasource_status="unverified")
                self.db.add(company)
                self.db.flush()
            source_key = "silver:" + key
            job = self.db.query(JobPosting).filter_by(source_key=source_key).one_or_none()
            if job is None:
                job = JobPosting(source_key=source_key, name=source_key)
                self.db.add(job)
                counts["created"] += 1
            else:
                counts["updated"] += 1
            job.company_id = company.company_id
            job.title = row["job_name"].strip()
            job.raw_description = row["job_description"].strip()
            job.department = row.get("department")
            employment = row.get("employment_type")
            job.employment_type = EMPLOYMENT_TYPES.get(employment, 6) if employment else None
            job.source_platform = row.get("ats_name")
            job.source_url = row.get("job_url")
            job.source_job_id = row.get("source_job_id")
            job.bronze_id = str(row["bronze_id"]) if row.get("bronze_id") is not None else None
            for source, destination in (("job_uploaded_at", "posted_date"), ("ingested_at", "ingested_at")):
                value = row.get(source)
                if value is not None and not isinstance(value, datetime):
                    raise ValueError(f"{source} must be a database timestamp")
                setattr(job, destination, value)
            self.db.flush()
            # Missing/null represent no source locations; other non-array values
            # must not silently clear existing associations.
            locations = row.get("locations")
            if locations is None:
                locations = []
            if not isinstance(locations, (list, tuple)):
                raise TypeError("locations must be an array, not a delimited string")
            linked = {}
            for name in locations:
                if not isinstance(name, str) or not name.strip():
                    raise ValueError("Location names must be non-empty strings")
                canonical = normalized(name)
                location = self.db.query(Location).filter_by(normalized_name=canonical).one_or_none()
                if location is None:
                    location = Location(name=" ".join(name.split()), normalized_name=canonical)
                    self.db.add(location)
                    self.db.flush()
                linked[canonical] = location
            job.locations = list(linked.values())
            # Compatibility display field only; normalized associations are authoritative.
            job.job_location = " | ".join(item.name for item in job.locations) or None
            # No skills field means extraction has not run: preserve existing skills.
            sync_skills(self.db, job, row, cache=skill_cache)
            self.db.flush()
            sync_categories(self.db, job, row, cache=category_cache)
        return counts
