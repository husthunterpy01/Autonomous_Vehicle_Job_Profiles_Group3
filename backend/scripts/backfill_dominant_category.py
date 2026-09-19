"""One-off backfill: collapse each job's categories down to a single
dominant main_type, matching the invariant scrapers/service/llm/
category_hierarchy.py now enforces for newly-classified jobs. Jobs imported
before that fix existed may still have categories spanning more than one
main_type; this drops the minority group's job_category links (never the
Category rows themselves, which other jobs may still use).

Same tie-break rule as the scraper-side fix and the API's
_to_category_response(): group by main_type, keep the largest group, and on
a tie keep whichever group's first sub_type sorts first by
(taxonomy_version, normalized_name).

Run: python -m scripts.backfill_dominant_category
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from sqlalchemy.orm import Session, selectinload

from app.core.database import SessionLocal
from app.models import JobPosting

logger = logging.getLogger(__name__)

BACKUP_PATH = Path(__file__).resolve().parent.parent / "evidence" / "backfill_dominant_category_removed.json"


def _dominant_categories(categories):
    groups: dict[tuple[int, str | None], list] = {}
    for category in sorted(categories, key=lambda c: (c.taxonomy_version, c.normalized_name)):
        key = (category.taxonomy_version, category.main_type)
        groups.setdefault(key, []).append(category)
    if not groups:
        return []
    _, members = max(groups.items(), key=lambda item: len(item[1]))
    return members


def backfill(db: Session) -> dict:
    jobs = db.query(JobPosting).options(selectinload(JobPosting.categories)).all()
    removed_log = []
    jobs_changed = 0
    for job in jobs:
        categories = job.categories
        if len({c.main_type for c in categories}) <= 1:
            continue
        dominant = _dominant_categories(categories)
        dominant_ids = {c.category_id for c in dominant}
        removed = [c for c in categories if c.category_id not in dominant_ids]
        removed_log.append({
            "job_id": str(job.job_id),
            "title": job.title,
            "kept": [{"sub_type": c.sub_type, "main_type": c.main_type} for c in dominant],
            "removed": [{"sub_type": c.sub_type, "main_type": c.main_type} for c in removed],
        })
        job.categories = dominant
        jobs_changed += 1
    db.flush()
    return {
        "jobs_scanned": len(jobs),
        "jobs_changed": jobs_changed,
        "links_dropped": sum(len(entry["removed"]) for entry in removed_log),
        "removed_log": removed_log,
    }


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    db = SessionLocal()
    try:
        with db.begin():
            summary = backfill(db)
            BACKUP_PATH.write_text(json.dumps(summary["removed_log"], indent=2), encoding="utf-8")
        logger.info(
            "Backfill complete: %d/%d jobs changed, %d job_category links dropped. Removed-link audit log: %s",
            summary["jobs_changed"], summary["jobs_scanned"], summary["links_dropped"], BACKUP_PATH,
        )
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
