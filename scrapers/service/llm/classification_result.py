from __future__ import annotations

from typing import Any

from scrapers.service.llm.job_classifier import RelevanceDecision
from scrapers.service.llm.job_enricher import JobEnrichment


def classification_as_dict(
    relevance: RelevanceDecision, enrichment: JobEnrichment | None = None
) -> dict[str, Any]:
    return {
        "is_av_relevant": relevance.is_av_relevant,
        "confidence": relevance.confidence,
        "matched_keywords": list(relevance.matched_keywords),
        "categories": list(enrichment.categories) if enrichment else [],
        "skills": (
            [{"name": skill.name, "skill_type": skill.skill_type} for skill in enrichment.skills]
            if enrichment
            else []
        ),
    }
