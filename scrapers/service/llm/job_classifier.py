from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from scrapers.service.llm.json_response import (
    build_batch_prompt,
    parse_batch_response,
    parse_string_list,
)

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "job_classification.txt"
SIGNALS_PATH = Path(__file__).resolve().parents[2] / "prompts" / "av_relevance_signals.txt"

ALLOWED_CONFIDENCE = frozenset({"High", "Medium", "Low"})


@dataclass(frozen=True)
class RelevanceDecision:
    is_av_relevant: bool
    confidence: str
    matched_keywords: tuple[str, ...]


class JobClassifier:
    """AV-relevance-only screening for a batch of jobs in a single injected LLM call.

    Pass 1 of the pipeline: cheap (no category taxonomy in the prompt), so it
    can run over every job before the more expensive category/skill
    enrichment pass runs on the AV-relevant subset only.
    """

    def __init__(self, complete: Callable[[str], str]) -> None:
        self.complete = complete

    def classify(self, title: str, description: str) -> RelevanceDecision:
        results = self.classify_batch([{"id": "job", "title": title, "description": description}])
        if "job" not in results:
            raise ValueError("LLM did not return a usable relevance decision for this job")
        return results["job"]

    def classify_batch(self, jobs: Sequence[Mapping[str, str]]) -> dict[str, RelevanceDecision]:
        if not jobs:
            return {}
        expected_ids = [str(job["id"]) for job in jobs]
        response = self.complete(self.build_prompt(jobs))
        return self.parse_response(response, expected_ids)

    @staticmethod
    def build_prompt(jobs: Sequence[Mapping[str, str]]) -> str:
        signals = SIGNALS_PATH.read_text(encoding="utf-8")
        return build_batch_prompt(PROMPT_PATH, "{{av_relevance_signals}}", signals, jobs)

    @staticmethod
    def parse_response(response: str, expected_ids: Sequence[str]) -> dict[str, RelevanceDecision]:
        """Parse whatever the batch response contains; a truncated tail (missing or
        malformed entries) is reported by omission rather than failing the whole
        batch, so the caller can retry just those job ids."""
        return parse_batch_response(response, expected_ids, JobClassifier._parse_one, "relevance")

    @staticmethod
    def _parse_one(payload: Mapping[str, object]) -> RelevanceDecision:
        is_av_relevant = payload.get("is_av_relevant")
        if not isinstance(is_av_relevant, bool):
            raise ValueError("'is_av_relevant' must be a boolean")  # noqa: TRY004 - malformed LLM JSON, not a Python type error

        confidence = str(payload.get("confidence") or "").strip().title()
        if confidence not in ALLOWED_CONFIDENCE:
            raise ValueError(f"'confidence' must be one of {sorted(ALLOWED_CONFIDENCE)}")

        matched_keywords = parse_string_list(payload.get("matched_keywords", []))
        return RelevanceDecision(is_av_relevant, confidence, matched_keywords)
