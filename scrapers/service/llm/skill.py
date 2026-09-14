from __future__ import annotations

from dataclasses import dataclass

ALLOWED_SKILL_TYPES = frozenset(
    {"tool", "programming_language", "framework", "domain_concept", "certification"}
)


@dataclass(frozen=True)
class ExtractedSkill:
    name: str
    skill_type: str


def parse_skills(skills: object) -> tuple[ExtractedSkill, ...]:
    if not isinstance(skills, list):
        raise ValueError("'skills' must be a list")

    extracted: list[ExtractedSkill] = []
    seen: set[str] = set()
    for item in skills:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        skill_type = str(item.get("skill_type") or "").strip().casefold()
        normalized_name = name.casefold()
        if not name or skill_type not in ALLOWED_SKILL_TYPES or normalized_name in seen:
            continue
        extracted.append(ExtractedSkill(name=name, skill_type=skill_type))
        seen.add(normalized_name)
    return tuple(extracted)
