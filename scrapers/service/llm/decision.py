from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FilterDecision:
    job_id: str
    company: str
    job_title: str
    included: bool
    score: int
    reason: str
    matched_keywords: tuple[str, ...]
    excluded_title_keywords: tuple[str, ...]
    audit_category: str | None
    category_evidence: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "company": self.company,
            "job_title": self.job_title,
            "included": self.included,
            "score": self.score,
            "reason": self.reason,
            "matched_keywords": list(self.matched_keywords),
            "excluded_title_keywords": list(self.excluded_title_keywords),
            "audit_category": self.audit_category,
            "category_evidence": list(self.category_evidence),
        }

    def as_csv_dict(self) -> dict[str, Any]:
        row = self.as_dict()
        for field_name in (
            "matched_keywords",
            "excluded_title_keywords",
            "category_evidence",
        ):
            row[field_name] = "; ".join(row[field_name])
        return row
