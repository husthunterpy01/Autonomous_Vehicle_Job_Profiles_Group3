"""Imports extracted skill labels. Mirrors category_sync.py: touches only
skill/job_skill, nothing else on the job (locations, title, etc. are left
alone) - safe to run against a handoff that only carries identity + skills.
"""
from app.enums.skill_type import SkillType
from app.models import Skill
from app.services.job_identity import resolve_job
from app.utils.normalization import normalized

SKILL_TYPES = {skill_type.value for skill_type in SkillType}


def _validate_skills(skills) -> list[tuple[str, str, str]]:
    """Returns [(normalized_name, skill_type, display_name), ...]."""
    if not isinstance(skills, (list, tuple)):
        raise TypeError("skills must be an array; use [] to clear")
    parsed = []
    for item in skills:
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("name"), str)
            or not item["name"].strip()
            or item.get("skill_type") not in SKILL_TYPES
        ):
            raise ValueError("Invalid extracted skill")
        parsed.append((normalized(item["name"]), item["skill_type"], item["name"].strip()))
    return parsed


def _preload_skills(db, keys: set[tuple[str, str]]) -> dict[tuple[str, str], Skill]:
    """One query per distinct skill_type touched by this batch, instead of
    one SELECT per label per job (~15-40k round-trips on a full import)."""
    skill_types = {skill_type for _, skill_type in keys}
    if not skill_types:
        return {}
    rows = db.query(Skill).filter(Skill.skill_type.in_(skill_types)).all()
    return {(s.normalized_name, s.skill_type): s for s in rows}


def _collect_skill_keys(records) -> set[tuple[str, str]]:
    """Best-effort scan to size the preload query - a row with invalid
    skills just contributes nothing here; the real validation and error
    message still happen per-row in import_skills's own loop."""
    keys = set()
    for row in records:
        if not isinstance(row, dict) or "skills" not in row:
            continue
        try:
            parsed = _validate_skills(row["skills"])
        except (TypeError, ValueError):
            continue
        keys.update((norm_name, skill_type) for norm_name, skill_type, _ in parsed)
    return keys


def sync_skills(db, job, row, cache: dict | None = None):
    if "skills" not in row:
        return
    parsed = _validate_skills(row["skills"])
    if cache is None:
        cache = _preload_skills(db, {(norm_name, skill_type) for norm_name, skill_type, _ in parsed})
    linked = {}
    for norm_name, skill_type, display_name in parsed:
        key = (norm_name, skill_type)
        skill = cache.get(key)
        if skill is None:
            skill = Skill(skill_name=display_name, normalized_name=norm_name, skill_type=skill_type)
            db.add(skill)
            db.flush()
            cache[key] = skill
        linked[key] = skill
    job.skills = list(linked.values())
    db.flush()


def import_skills(db, records):
    """Caller owns transaction and writer serialization, as for import_categories."""
    if not isinstance(records, list):
        raise TypeError("Handoff must be a JSON array")
    cache = _preload_skills(db, _collect_skill_keys(records))
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
            sync_skills(db, job, row, cache=cache)
            updated += int("skills" in row)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Row {index + 1}: {exc}") from exc
    return {"read": len(records), "updated": updated}
