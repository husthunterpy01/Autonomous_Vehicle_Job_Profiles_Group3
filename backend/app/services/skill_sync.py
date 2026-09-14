"""Imports extracted skill labels. Mirrors category_sync.py: touches only
skill/job_skill, nothing else on the job (locations, title, etc. are left
alone) - safe to run against a handoff that only carries identity + skills.
"""
from app.models import Skill
from app.services.job_identity import resolve_job
from app.utils.normalization import normalized

SKILL_TYPES = {"tool", "programming_language", "framework", "domain_concept", "certification"}


def sync_skills(db, job, row):
    if "skills" not in row:
        return
    skills = row["skills"]
    if not isinstance(skills, (list, tuple)):
        raise TypeError("skills must be an array; use [] to clear")
    linked = {}
    for item in skills:
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("name"), str)
            or not item["name"].strip()
            or item.get("skill_type") not in SKILL_TYPES
        ):
            raise ValueError("Invalid extracted skill")
        key = (normalized(item["name"]), item["skill_type"])
        skill = db.query(Skill).filter_by(normalized_name=key[0], skill_type=key[1]).one_or_none()
        if skill is None:
            skill = Skill(skill_name=item["name"].strip(), normalized_name=key[0], skill_type=key[1])
            db.add(skill)
            db.flush()
        linked[key] = skill
    job.skills = list(linked.values())
    db.flush()


def import_skills(db, records):
    """Caller owns transaction and writer serialization, as for import_categories."""
    if not isinstance(records, list):
        raise TypeError("Handoff must be a JSON array")
    seen = set()
    updated = 0
    for index, row in enumerate(records):
        try:
            if not isinstance(row, dict):
                raise TypeError("Each record must be an object")
            job = resolve_job(db, row)
            if job.job_id in seen:
                raise ValueError("Multiple handoff records target the same backend job")
            seen.add(job.job_id)
            sync_skills(db, job, row)
            updated += int("skills" in row)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Row {index + 1}: {exc}") from exc
    return {"read": len(records), "updated": updated}
