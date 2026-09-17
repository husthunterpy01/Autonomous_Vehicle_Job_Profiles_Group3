from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from scrapers.service.llm.json_response import (
    build_batch_prompt,
    parse_batch_response,
    parse_string_list,
)
from scrapers.service.llm.skill import ExtractedSkill, parse_skills

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "job_enrichment.txt"
CATEGORIES_PATH = Path(__file__).resolve().parents[2] / "prompts" / "categories_definition.txt"

ALLOWED_CATEGORIES = frozenset(
    {
        "Sensing",
        "Localization",
        "Perception",
        "Prediction",
        "Planning",
        "Control",
        "Vehicle Interface",
        "Mapping",
        "System and Safety",
    }
)


@dataclass(frozen=True)
class JobEnrichment:
    categories: tuple[str, ...]
    skills: tuple[ExtractedSkill, ...]


class JobEnricher:
    """Category and skill extraction for a batch of already AV-confirmed jobs.

    Pass 2 of the pipeline: only run on jobs JobClassifier has already marked
    AV-relevant, so the taxonomy/skill-normalization prompt overhead is paid
    once per batch of true AV jobs rather than for every job in bronze/silver.
    """

    def __init__(self, complete: Callable[[str], str]) -> None:
        self.complete = complete

    def enrich(self, title: str, description: str) -> JobEnrichment:
        results = self.enrich_batch([{"id": "job", "title": title, "description": description}])
        if "job" not in results:
            raise ValueError("LLM did not return a usable enrichment for this job")
        return results["job"]

    def enrich_batch(self, jobs: Sequence[Mapping[str, str]]) -> dict[str, JobEnrichment]:
        if not jobs:
            return {}
        expected_ids = [str(job["id"]) for job in jobs]
        response = self.complete(self.build_prompt(jobs))
        return self.parse_response(response, expected_ids)

    @staticmethod
    def build_prompt(jobs: Sequence[Mapping[str, str]]) -> str:
        categories_definition = CATEGORIES_PATH.read_text(encoding="utf-8")
        return build_batch_prompt(PROMPT_PATH, "{{categories_definition}}", categories_definition, jobs)

    @staticmethod
    def parse_response(response: str, expected_ids: Sequence[str]) -> dict[str, JobEnrichment]:
        """Parse whatever the batch response contains; a truncated tail (missing or
        malformed entries) is reported by omission rather than failing the whole
        batch, so the caller can retry just those job ids."""
        return parse_batch_response(response, expected_ids, JobEnricher._parse_one, "enrichment")

    @staticmethod
    def _parse_one(payload: Mapping[str, object]) -> JobEnrichment:
        categories = parse_string_list(payload.get("categories"))
        unknown_categories = [name for name in categories if name not in ALLOWED_CATEGORIES]
        if unknown_categories:
            raise ValueError(f"Unknown categories in LLM response: {unknown_categories}")
        if not categories:
            raise ValueError("AV-relevant jobs must include at least one category")

        skills = parse_skills(payload.get("skills", []))
        return JobEnrichment(categories, skills)
