"""Normalize Silver rows into backend tables within the caller's transaction."""
from collections.abc import Iterable, Mapping
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Company, JobPosting, Location, Skill

EMPLOYMENT_TYPES = {"full-time": 1, "part-time": 2, "contract": 3, "temporary": 4, "internship": 5}
SKILL_TYPES = {"tool", "programming_language", "framework", "domain_concept", "certification"}


def normalized(value: str) -> str:
    return " ".join(value.split()).lower()


class SilverSync:
    def __init__(self, db: Session):
        self.db = db

    def run(self, records: Iterable[Mapping]) -> dict[str, int]:
        counts = {"read": 0, "created": 0, "updated": 0}
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
            locations = row.get("locations") or []
            if not isinstance(locations, (list, tuple)):
                raise ValueError("locations must be an array, not a delimited string")
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
            if "skills" in row:
                if not isinstance(row["skills"], (list, tuple)):
                    raise ValueError("skills must be an array")
                skills = {}
                for item in row["skills"]:
                    if not isinstance(item, Mapping) or not isinstance(item.get("name"), str) or not item["name"].strip() or item.get("skill_type") not in SKILL_TYPES:
                        raise ValueError("Invalid extracted skill")
                    skill_key = (normalized(item["name"]), item["skill_type"])
                    skill = self.db.query(Skill).filter_by(normalized_name=skill_key[0], skill_type=skill_key[1]).one_or_none()
                    if skill is None:
                        skill = Skill(skill_name=item["name"].strip(), normalized_name=skill_key[0], skill_type=skill_key[1])
                        self.db.add(skill)
                        self.db.flush()
                    skills[skill_key] = skill
                job.skills = list(skills.values())
            self.db.flush()
        return counts
