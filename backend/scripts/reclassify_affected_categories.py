"""One-off remediation: the 393 jobs in backfill_dominant_category_removed.json
had their category picked by an alphabetical tie-break bug (now fixed in
category_sync.dominant_categories), not by real classifier signal. Their
job_category link to the losing group is already gone - there is nothing
left in the database to re-derive a correct answer from, so this re-runs
the real classification pipeline (keyword-first, Groq fallback, same as
scrapers/utils/job_enricher.py) against each job's stored title/
raw_description, then re-imports just the resulting categories through the
now-fixed sync_categories (skills are left untouched - this bug never
touched them).

Run from backend/: python -m scripts.reclassify_affected_categories
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

from scrapers.service.llm import (
    JobEnricher,
    KeywordCategoryClassifier,
)
from scrapers.service.llm.groq_client import GroqCompletion
from scrapers.service.llm.text import compress_job_text

from app.core.database import SessionLocal
from app.models import JobPosting
from app.services.category_sync import sync_categories

logger = logging.getLogger(__name__)

AUDIT_LOG_PATH = Path(__file__).resolve().parent.parent / "evidence" / "backfill_dominant_category_removed.json"
MAX_DESCRIPTION_CHARS = 1200
BATCH_SIZE = 10


def _load_affected_job_ids() -> list[str]:
    with AUDIT_LOG_PATH.open(encoding="utf-8") as stream:
        entries = json.load(stream)
    return [entry["job_id"] for entry in entries]


def _chunk(items: list, size: int) -> list[list]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def reclassify(db) -> dict:
    job_ids = _load_affected_job_ids()
    jobs = db.query(JobPosting).filter(JobPosting.job_id.in_(job_ids)).all()
    logger.info("Loaded %d/%d affected jobs from the database.", len(jobs), len(job_ids))

    keyword_classifier = KeywordCategoryClassifier()
    enricher = JobEnricher(GroqCompletion())

    keyword_resolved = 0
    llm_resolved = 0
    unresolved: list[str] = []
    changed = 0

    needs_llm: list[JobPosting] = []
    compressed_by_job: dict = {}
    for job in jobs:
        title, description = compress_job_text(job.title, job.raw_description, MAX_DESCRIPTION_CHARS)
        compressed_by_job[job.job_id] = (title, description)
        categories = keyword_classifier.classify(f"{title} {description}")
        if categories:
            if sorted(categories) != sorted(c.sub_type for c in job.categories):
                changed += 1
            sync_categories(db, job, {"functional_area": list(categories)})
            keyword_resolved += 1
        else:
            needs_llm.append(job)

    logger.info("Keyword pass resolved %d/%d jobs; %d need Groq.", keyword_resolved, len(jobs), len(needs_llm))

    batches = _chunk(needs_llm, BATCH_SIZE)
    for batch_index, batch in enumerate(batches, start=1):
        jobs_by_id = {}
        for job in batch:
            title, description = compressed_by_job[job.job_id]
            jobs_by_id[str(job.job_id)] = {"id": str(job.job_id), "title": title, "description": description}
        try:
            results = enricher.enrich_batch(list(jobs_by_id.values()))
        except Exception as exc:  # noqa: BLE001 - one bad batch shouldn't stop the whole remediation
            logger.error("Batch %d failed outright: %s", batch_index, exc)
            results = {}

        for job in batch:
            enrichment = results.get(str(job.job_id))
            if enrichment is None or not enrichment.categories:
                unresolved.append(str(job.job_id))
                continue
            if sorted(enrichment.categories) != sorted(c.sub_type for c in job.categories):
                changed += 1
            sync_categories(db, job, {"functional_area": list(enrichment.categories)})
            llm_resolved += 1
        logger.info("LLM batch %d/%d done.", batch_index, len(batches))

    db.flush()
    return {
        "total_affected": len(job_ids),
        "found_in_db": len(jobs),
        "keyword_resolved": keyword_resolved,
        "llm_resolved": llm_resolved,
        "unresolved": unresolved,
        "changed_from_backfill_pick": changed,
    }


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    db = SessionLocal()
    try:
        with db.begin():
            summary = reclassify(db)
        logger.info("Reclassification complete: %s", json.dumps(summary, indent=2))
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
