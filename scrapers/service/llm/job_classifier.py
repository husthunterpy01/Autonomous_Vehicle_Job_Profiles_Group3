from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from scrapers.service.llm.json_response import parse_string_list, strip_code_fence
from scrapers.service.llm.text import normalize_text

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
        template = PROMPT_PATH.read_text(encoding="utf-8")
        signals = SIGNALS_PATH.read_text(encoding="utf-8")
        jobs_payload = [
            {
                "id": str(job["id"]),
                "title": normalize_text(job.get("title", "")),
                "description": normalize_text(job.get("description", "")),
            }
            for job in jobs
        ]
        jobs_json = json.dumps(jobs_payload, ensure_ascii=False)
        return template.replace("{{av_relevance_signals}}", signals).replace("{{jobs_json}}", jobs_json)

    @staticmethod
    def parse_response(response: str, expected_ids: Sequence[str]) -> dict[str, RelevanceDecision]:
        """Parse whatever the batch response contains; a truncated tail (missing or
        malformed entries) is reported by omission rather than failing the whole
        batch, so the caller can retry just those job ids."""
        payload = json.loads(strip_code_fence(response))
        if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
            raise ValueError("LLM relevance response must be a JSON object with a 'results' array")  # noqa: TRY004 - malformed LLM JSON, not a Python type error

        expected = set(expected_ids)
        results: dict[str, RelevanceDecision] = {}
        for item in payload["results"]:
            if not isinstance(item, dict):
                continue
            job_id = str(item.get("id") or "").strip()
            if job_id not in expected or job_id in results:
                continue
            try:
                results[job_id] = JobClassifier._parse_one(item)
            except ValueError:
                continue
        return results

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
