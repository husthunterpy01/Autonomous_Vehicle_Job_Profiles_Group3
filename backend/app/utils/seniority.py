"""Seniority level inferred from a job title."""
import re

from app.enums.seniority_type import SeniorityLevel

# Highest rank first: "Senior Engineering Manager" is a manager, "Senior / Staff" is staff.
_RULES = (
    (SeniorityLevel.CEO, r"chief|\bceo\b|\bcto\b|\bcoo\b|\bcfo\b|co-?founder|\bfounder\b"),
    (SeniorityLevel.DIRECTOR, r"director|\bvp\b|vice president|head of"),
    (SeniorityLevel.MANAGER, r"manager|\bmgr\b"),
    (SeniorityLevel.PRINCIPAL, r"principal|\bstaff\b|distinguished|\bfellow\b"),
    (SeniorityLevel.LEAD, r"\blead\b|\bleader\b"),
    (SeniorityLevel.SENIOR, r"senior|\bsr\b|\biii\b|\biv\b"),
    (SeniorityLevel.JUNIOR, r"junior|\bjr\b|intern(ship)?\b|graduate|entry[- ]level|new grad|apprentice|working student|co-?op\b|trainee"),
)
_COMPILED = tuple((level, re.compile(pattern, re.IGNORECASE)) for level, pattern in _RULES)


def infer_seniority(title: str | None) -> SeniorityLevel:
    """MID when the title carries no level word."""
    for level, pattern in _COMPILED:
        if pattern.search(title or ""):
            return level
    return SeniorityLevel.MID
