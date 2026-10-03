"""One-off backfill: refresh job_location links for jobs already imported
whose Silver source row has gained `locations` since they were first synced
(the classification file pipeline has its own resume logic that leaves
already-processed jobs on their original, sometimes location-less, Silver
snapshot forever - see the investigation this script follows up on).

Deliberately narrower than `app.sync_silver`: this only touches jobs that
already exist in the backend (matched by source_key = "silver:" +
deduplication_key, the same convention SilverSync/resolve_job use). It
never creates a JobPosting, Company, or any other row, and it never reads
`SilverSync.run()`'s is_av_relevant filter - a missing match here just
means "this Silver row was never imported," which is the correct, expected
outcome for anything the classification pipeline rejected, and it's left
alone.

Requires SILVER_DATABASE_URL (the database containing
silver.cleaned_job_postings) in addition to this app's usual DATABASE_URL.

Run: python -m scripts.backfill_job_locations [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, selectinload

from app.core.database import SessionLocal
from app.models import JobPosting, Location
from app.utils.normalization import normalized

logger = logging.getLogger(__name__)

BACKUP_PATH = Path(__file__).resolve().parent.parent / "evidence" / "backfill_job_locations_changed.json"

SELECT_SQL = "SELECT deduplication_key, locations FROM silver.cleaned_job_postings ORDER BY deduplication_key"


def _link_locations(db: Session, job: JobPosting, names: list[str], cache: dict[str, Location]) -> list[str]:
    linked: dict[str, Location] = {}
    for name in names:
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"Location names must be non-empty strings (job {job.job_id})")
        canonical = normalized(name)
        location = cache.get(canonical)
        if location is None:
            location = db.query(Location).filter_by(normalized_name=canonical).one_or_none()
            if location is None:
                location = Location(name=" ".join(name.split()), normalized_name=canonical)
                db.add(location)
                db.flush()
            cache[canonical] = location
        linked[canonical] = location
    job.locations = list(linked.values())
    return sorted(linked)


def backfill(db: Session, silver_rows: list[dict], *, dry_run: bool) -> dict:
    # Preloaded once instead of one query per Silver row - against a remote
    # pooler (Supabase) the per-row version turns ~5,300 rows into ~5,300
    # round trips and never finishes in practical time. Same reasoning as
    # SilverSync's own category/skill preload.
    jobs_by_source_key: dict[str, JobPosting] = {
        job.source_key: job
        for job in db.query(JobPosting)
        .options(selectinload(JobPosting.locations))
        .filter(JobPosting.source_key.like("silver:%"))
    }
    location_cache: dict[str, Location] = {
        location.normalized_name: location for location in db.query(Location)
    }
    changed_log = []
    matched = unmatched = unchanged = changed = 0

    for row in silver_rows:
        key = row.get("deduplication_key")
        if not isinstance(key, str) or not key.strip():
            raise ValueError("Every Silver row requires a deduplication_key")
        locations = row.get("locations")
        if locations is None:
            locations = []
        if not isinstance(locations, (list, tuple)):
            raise TypeError(f"locations must be an array, not a delimited string (key {key})")

        job = jobs_by_source_key.get("silver:" + key)
        if job is None:
            unmatched += 1
            continue
        matched += 1

        before = sorted(normalized(location.name) for location in job.locations)
        after_list = list(locations)
        after = sorted(normalized(name) for name in after_list if isinstance(name, str))
        if before == after:
            unchanged += 1
            continue

        new_names = _link_locations(db, job, after_list, location_cache)
        changed += 1
        changed_log.append({
            "job_id": str(job.job_id),
            "title": job.title,
            "source_key": job.source_key,
            "before": before,
            "after": new_names,
        })

    if dry_run:
        db.rollback()

    return {
        "silver_rows_read": len(silver_rows),
        "matched_existing_jobs": matched,
        "unmatched_silver_rows": unmatched,
        "unchanged": unchanged,
        "changed": changed,
        "changed_log": changed_log,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Report what would change without committing")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    silver_url = os.environ.get("SILVER_DATABASE_URL")
    if not silver_url:
        raise ValueError("Set SILVER_DATABASE_URL to the database containing silver.cleaned_job_postings")
    silver_engine = create_engine(silver_url, pool_pre_ping=True)
    try:
        with silver_engine.connect() as connection:
            silver_rows = [dict(row) for row in connection.execute(text(SELECT_SQL)).mappings()]
    finally:
        silver_engine.dispose()
    logger.info("Read %d rows from silver.cleaned_job_postings.", len(silver_rows))

    db = SessionLocal()
    try:
        with db.begin():
            summary = backfill(db, silver_rows, dry_run=args.dry_run)
        if not args.dry_run and summary["changed_log"]:
            BACKUP_PATH.parent.mkdir(parents=True, exist_ok=True)
            BACKUP_PATH.write_text(json.dumps(summary["changed_log"], indent=2), encoding="utf-8")
        logger.info(
            "%s%d/%d Silver rows matched an existing job; %d changed, %d already correct, %d had no matching job.",
            "[DRY RUN] " if args.dry_run else "",
            summary["matched_existing_jobs"], summary["silver_rows_read"],
            summary["changed"], summary["unchanged"], summary["unmatched_silver_rows"],
        )
        if summary["changed"] and not args.dry_run:
            logger.info("Changed-job audit log: %s", BACKUP_PATH)
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
