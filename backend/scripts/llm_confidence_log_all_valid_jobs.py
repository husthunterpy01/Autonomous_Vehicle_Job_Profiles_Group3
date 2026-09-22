"""Read-only: run every AV-relevant (already-categorized) job through the
confidence-aware JobEnricher LLM path directly - bypassing the keyword-first
shortcut, so every job actually hits Groq and reports real confidence
values - and log the results, including any real ties the tie-break logic
had to resolve. Writes nothing to the database; existing job_category links
are untouched.

Appends one JSON line per job to OUTPUT_PATH as each batch completes, so
progress survives an interruption and can be resumed by re-running (already
logged job ids are skipped).

Run from backend/: python -m scripts.llm_confidence_log_all_valid_jobs
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv

load_dotenv(REPO_ROOT / "scrapers" / ".env")
load_dotenv(REPO_ROOT / ".env")

from scrapers.service.llm import JobEnricher
from scrapers.service.llm.category_hierarchy import (
    constrain_to_dominant_main_type,
    load_main_types,
)
from scrapers.service.llm.groq_client import GroqCompletion
from scrapers.service.llm.job_enricher import (
    _CONFIDENCE_WEIGHTS,
    ALLOWED_CATEGORIES,
    parse_categories_with_confidence,
)
from scrapers.service.llm.json_response import strip_code_fence
from scrapers.service.llm.text import compress_job_text
from scrapers.utils.job_classifier import _batch_call_with_retry

from app.core.database import SessionLocal
from app.models import JobPosting

logger = logging.getLogger(__name__)

OUTPUT_PATH = Path(__file__).resolve().parent / "llm_confidence_log_all_valid_jobs.jsonl"
MAX_DESCRIPTION_CHARS = 1200
BATCH_SIZE = 10


def _chunk(items: list, size: int) -> list[list]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def _load_already_logged_ids() -> set[str]:
    """Only rows that actually resolved count as done - an error row (e.g.
    from a truncated batch response with no retry) must be eligible for
    retry on the next run, not skipped forever."""
    if not OUTPUT_PATH.is_file():
        return set()
    seen = set()
    with OUTPUT_PATH.open("r", encoding="utf-8") as stream:
        for line in stream:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if "error" not in row:
                seen.add(row["job_id"])
    return seen


def _drop_prior_error_rows_for(job_ids: set[str]) -> None:
    """Remove any previously-logged error rows for jobs we're about to
    retry, so a successful retry doesn't leave a stale error row sitting
    alongside it in the output file."""
    if not OUTPUT_PATH.is_file() or not job_ids:
        return
    lines = OUTPUT_PATH.read_text(encoding="utf-8").splitlines()
    kept = [line for line in lines if not (json.loads(line)["job_id"] in job_ids and "error" in json.loads(line))]
    OUTPUT_PATH.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")


def _log_row(job_id: str, title: str, existing: list[str], main_types: dict, payload: object) -> dict:
    row = {"job_id": job_id, "title": title, "existing_db_categories": existing}
    if not isinstance(payload, dict):
        row["error"] = "malformed result payload"
        return row
    try:
        categories_with_confidence = parse_categories_with_confidence(payload.get("categories"))
    except ValueError as exc:
        row["error"] = f"parse error: {exc}"
        return row

    names = tuple(n for n, _ in categories_with_confidence)
    unknown = [n for n in names if n not in ALLOWED_CATEGORIES]
    if unknown or not names:
        row["error"] = f"unknown or missing categories: {unknown or 'none returned'}"
        row["raw_categories"] = categories_with_confidence
        return row

    weights = {n: _CONFIDENCE_WEIGHTS[c] for n, c in categories_with_confidence}
    groups: dict[str, list[str]] = {}
    for name, confidence in categories_with_confidence:
        group = main_types.get(name, name)
        groups.setdefault(group, []).append(f"{name}:{confidence}")
    winner = constrain_to_dominant_main_type(names, weights=weights)

    row["llm_said"] = groups
    row["kept_categories"] = list(winner)
    row["kept_main_type"] = main_types.get(winner[0]) if winner else None
    row["was_a_real_tie"] = len(groups) > 1
    return row


def _call_batch_raw(enricher: JobEnricher, jobs: list[dict]) -> dict[str, dict]:
    """call_batch for _batch_call_with_retry: returns the raw {id: payload}
    dict (before parse_categories_with_confidence) so the log can keep the
    real per-category confidence values, not just JobEnricher's already-
    resolved JobEnrichment.categories."""
    response = enricher.complete(enricher.build_prompt(jobs))
    raw = json.loads(strip_code_fence(response))
    expected_ids = {str(job["id"]) for job in jobs}
    return {
        str(item.get("id")): item
        for item in raw.get("results", [])
        if isinstance(item, dict) and str(item.get("id")) in expected_ids
    }


def run() -> dict:
    db = SessionLocal()
    jobs = db.query(JobPosting).join(JobPosting.categories).distinct().all()
    logger.info("Loaded %d AV-relevant (already-categorized) jobs.", len(jobs))

    already_logged = _load_already_logged_ids()
    pending = [job for job in jobs if str(job.job_id) not in already_logged]
    _drop_prior_error_rows_for({str(job.job_id) for job in pending})
    logger.info("%d already resolved from a previous run; %d remaining (incl. retries of prior errors).",
                len(already_logged), len(pending))

    main_types = load_main_types()
    enricher = JobEnricher(GroqCompletion())
    batches = _chunk(pending, BATCH_SIZE)

    with OUTPUT_PATH.open("a", encoding="utf-8") as out:
        for batch_index, batch in enumerate(batches, start=1):
            jobs_by_id = {}
            existing_by_id = {}
            for job in batch:
                title, description = compress_job_text(job.title, job.raw_description, MAX_DESCRIPTION_CHARS)
                jobs_by_id[str(job.job_id)] = {"id": str(job.job_id), "title": title, "description": description}
                existing_by_id[str(job.job_id)] = sorted(c.sub_type for c in job.categories)

            payloads_by_id = _batch_call_with_retry(
                lambda batch_jobs: _call_batch_raw(enricher, batch_jobs),
                jobs_by_id, batch_index, len(batches), label="confidence-log",
            )

            for job_id, job_payload in jobs_by_id.items():
                payload = payloads_by_id.get(job_id)
                if payload is None:
                    row = {"job_id": job_id, "title": job_payload["title"],
                           "existing_db_categories": existing_by_id[job_id],
                           "error": "no usable response after retry"}
                else:
                    row = _log_row(job_id, job_payload["title"], existing_by_id[job_id], main_types, payload)
                out.write(json.dumps(row) + "\n")
            out.flush()
            logger.info("Batch %d/%d done (%d jobs).", batch_index, len(batches), len(batch))

    return {"total_jobs": len(jobs), "already_resolved": len(already_logged), "newly_processed": len(pending)}


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    summary = run()
    logger.info("Run complete: %s", json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
