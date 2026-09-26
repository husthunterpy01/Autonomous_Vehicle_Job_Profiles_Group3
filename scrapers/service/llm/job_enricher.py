from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from scrapers.service.llm.category_hierarchy import (
    constrain_to_dominant_main_type,
    load_main_types,
)
from scrapers.service.llm.json_response import (
    build_batch_prompt,
    parse_batch_response,
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
        "Infrastructure",
    }
)

# How strongly the model itself says a category applies, used only to weight
# constrain_to_dominant_main_type's tie-break (see _parse_one) - never
# stored or exposed beyond that, since JobEnrichment.categories is still a
# plain tuple of names.
_CONFIDENCE_WEIGHTS = {"High": 3, "Medium": 2, "Low": 1}


def parse_categories_with_confidence(value: object) -> tuple[tuple[str, str], ...]:
    """Returns ((category_name, confidence), ...) in response order, deduped
    by name (first occurrence wins) - mirrors parse_skills's shape-validation
    style for a list of {name, confidence} objects."""
    if not isinstance(value, list):
        raise ValueError("'categories' must be a list")  # noqa: TRY004 - malformed LLM JSON, not a Python type error

    parsed: list[tuple[str, str]] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, dict):
            raise ValueError("Each category entry must be an object with 'name' and 'confidence'")  # noqa: TRY004
        name = str(item.get("name") or "").strip()
        confidence = str(item.get("confidence") or "").strip().title()
        if not name:
            raise ValueError("Category entries must have a non-empty 'name'")
        if confidence not in _CONFIDENCE_WEIGHTS:
            raise ValueError(f"Category confidence must be one of {sorted(_CONFIDENCE_WEIGHTS)}")
        if name in seen:
            continue
        parsed.append((name, confidence))
        seen.add(name)
    return tuple(parsed)


@dataclass(frozen=True)
class JobEnrichment:
    """`categories` is empty when the model explicitly found no category that
    fits the role - by design that means "not AV engineering", not "pick the
    closest one": there is deliberately no fallback category (see
    categories_definition.txt), and JobEnricherMain drops such jobs.

    `area` and `evidence` are the model's stated technical area and the
    phrase from the posting that justifies the choice; kept for audit only.
    """

    categories: tuple[str, ...]
    skills: tuple[ExtractedSkill, ...]
    area: str = ""
    evidence: str = ""

    @property
    def has_category(self) -> bool:
        return bool(self.categories)


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
        categories_with_confidence = parse_categories_with_confidence(payload.get("categories"))
        names = tuple(name for name, _ in categories_with_confidence)
        unknown_categories = [name for name in names if name not in ALLOWED_CATEGORIES]
        if unknown_categories:
            raise ValueError(f"Unknown categories in LLM response: {unknown_categories}")
        area = str(payload.get("area") or "").strip()
        evidence = str(payload.get("evidence") or "").strip()
        if not names:
            # An explicit empty list is a valid "no category fits" answer.
            # A missing/non-list "categories" already raised above, so a
            # truncated or malformed entry is still retried, never dropped.
            return JobEnrichment((), (), area, evidence)

        # A job gets exactly one main_type (see category_hierarchy.py) even
        # when the LLM proposes sub_types spanning more than one - keep only
        # the dominant group's sub_types rather than trusting the raw
        # cross-group list. Weighting by the model's own reported confidence
        # (instead of just counting matched sub_types) lets one
        # strongly-evidenced category outweigh two weakly-evidenced ones in
        # a different group, and gives ties a real signal to break on
        # instead of falling back to response order.
        weights = {name: _CONFIDENCE_WEIGHTS[confidence] for name, confidence in categories_with_confidence}
        # The prompt makes the model commit to one technical area first; when
        # it did and that area is one we know, honor it over the
        # confidence-weighted guess so the two steps can't disagree.
        main_types = load_main_types()
        if area in set(main_types.values()):
            in_area = tuple(name for name in names if main_types.get(name) == area)
            categories = constrain_to_dominant_main_type(in_area, weights=weights) if in_area else ()
            if not categories:
                categories = constrain_to_dominant_main_type(names, weights=weights)
        else:
            categories = constrain_to_dominant_main_type(names, weights=weights)
        skills = parse_skills(payload.get("skills", []))
        return JobEnrichment(categories, skills, area, evidence)
