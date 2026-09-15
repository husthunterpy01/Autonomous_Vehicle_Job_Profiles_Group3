from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import TypeVar

from scrapers.service.llm.text import normalize_text

T = TypeVar("T")


def strip_code_fence(text: str) -> str:
    """Strip a ```json ... ``` or ``` ... ``` fence an LLM sometimes wraps JSON in."""
    text = text.strip()
    if not text.startswith("```"):
        return text
    lines = text.splitlines()
    text = "\n".join(lines[1:-1])
    if text.lstrip().startswith("json"):
        text = text.lstrip()[4:].lstrip()
    return text


def build_batch_prompt(
    template_path: Path,
    placeholder: str,
    placeholder_value: str,
    jobs: Sequence[Mapping[str, str]],
) -> str:
    """Shared by JobClassifier and JobEnricher: substitute the jobs-json
    payload plus one task-specific placeholder (relevance signals or the
    category taxonomy) into a prompt template."""
    template = template_path.read_text(encoding="utf-8")
    jobs_payload = [
        {
            "id": str(job["id"]),
            "title": normalize_text(job.get("title", "")),
            "description": normalize_text(job.get("description", "")),
        }
        for job in jobs
    ]
    jobs_json = json.dumps(jobs_payload, ensure_ascii=False)
    return template.replace(placeholder, placeholder_value).replace("{{jobs_json}}", jobs_json)


def parse_batch_response(
    response: str,
    expected_ids: Sequence[str],
    parse_one: Callable[[Mapping[str, object]], T],
    error_label: str,
) -> dict[str, T]:
    """Shared by JobClassifier and JobEnricher: parse whatever the batch
    response contains, keeping only entries matching an expected id and
    handing each to `parse_one`. A truncated tail (missing or malformed
    entries) is reported by omission rather than failing the whole batch, so
    the caller can retry just those job ids."""
    payload = json.loads(strip_code_fence(response))
    if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
        raise ValueError(f"LLM {error_label} response must be a JSON object with a 'results' array")  # noqa: TRY004 - malformed LLM JSON, not a Python type error

    expected = set(expected_ids)
    results: dict[str, T] = {}
    for item in payload["results"]:
        if not isinstance(item, dict):
            continue
        job_id = str(item.get("id") or "").strip()
        if job_id not in expected or job_id in results:
            continue
        try:
            results[job_id] = parse_one(item)
        except ValueError:
            continue
    return results


def parse_string_list(value: object) -> tuple[str, ...]:
    """Validate a JSON array of strings and dedupe it, preserving order."""
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError("Expected a JSON array of strings")
    seen: set[str] = set()
    deduped: list[str] = []
    for item in value:
        stripped = item.strip()
        if stripped and stripped not in seen:
            deduped.append(stripped)
            seen.add(stripped)
    return tuple(deduped)
