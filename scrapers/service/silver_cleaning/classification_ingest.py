"""DOC-13: land one scrape run's classification output in silver.

Silver is the last layer that cleans data: this validates each row of the
run's av_jobs.jsonl, normalizes skill names and resolves the job's
main_type, then writes three primitive silver tables. The gold dbt models
(models/gold, tag "gold") only reshape these into the star schema - no
further sanitizing happens after silver.

    python -m scrapers.service.silver_cleaning.classification_ingest \
        data/job_classification/av_jobs.jsonl --scraped-at 2026-08-31T14:17:29Z
"""
import argparse
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values
from scrapers.config.dbt import DbtConfig
from scrapers.config.postgres import PostgresConfig
from scrapers.service.llm.category_hierarchy import load_main_types

logger = logging.getLogger(__name__)

RUN_SOURCES = ("live", "backfill")
# Same values as the backend SkillType enum.
SKILL_TYPES = frozenset({"tool", "programming_language", "framework", "domain_concept", "certification"})
_DEDUP_KEY = re.compile(r"^[0-9a-f]{32}$")

TABLES_SQL = """
CREATE SCHEMA IF NOT EXISTS silver;

-- One row per scrape run. Only a completed run has jobs; a failed or
-- partial run is registered with completed = false so it can never become
-- a month's snapshot.
CREATE TABLE IF NOT EXISTS silver.classification_run (
    scraped_at timestamptz PRIMARY KEY,
    source text NOT NULL CHECK (source IN ('live', 'backfill')),
    classifier_version text,
    completed boolean NOT NULL,
    jobs_seen integer NOT NULL CHECK (jobs_seen >= 0),
    ingested_at timestamptz NOT NULL DEFAULT now()
);

-- One row per (run, AV job).
CREATE TABLE IF NOT EXISTS silver.classified_job (
    scraped_at timestamptz NOT NULL REFERENCES silver.classification_run (scraped_at) ON DELETE CASCADE,
    deduplication_key text NOT NULL CHECK (deduplication_key ~ '^[0-9a-f]{32}$'),
    job_title text NOT NULL,
    main_type text,
    PRIMARY KEY (scraped_at, deduplication_key)
);

-- One row per (run, AV job, skill). skill_name is normalized like the
-- backend skill table (whitespace collapsed, lower case).
CREATE TABLE IF NOT EXISTS silver.classified_job_skill (
    scraped_at timestamptz NOT NULL,
    deduplication_key text NOT NULL,
    skill_name text NOT NULL,
    skill_type text NOT NULL CHECK (skill_type IN ('tool', 'programming_language', 'framework', 'domain_concept', 'certification')),
    display_name text NOT NULL,
    PRIMARY KEY (scraped_at, deduplication_key, skill_name, skill_type),
    FOREIGN KEY (scraped_at, deduplication_key)
        REFERENCES silver.classified_job (scraped_at, deduplication_key) ON DELETE CASCADE
);
"""


@dataclass(frozen=True)
class ClassifiedJob:
    deduplication_key: str
    title: str
    main_type: str | None
    skills: tuple[tuple[str, str, str], ...]  # (skill_name, skill_type, display_name)


def parse_scraped_at(value: str) -> datetime:
    """ISO 8601 with a timezone; "Z" is accepted for UTC."""
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"scraped_at is not an ISO 8601 timestamp: {value!r}") from exc
    if parsed.tzinfo is None:
        raise ValueError("scraped_at must include a timezone, e.g. 2026-08-31T12:00:00Z")
    return parsed


def read_jsonl(path: Path) -> list:
    records = []
    with path.open("r", encoding="utf-8-sig") as stream:
        for number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Line {number}: invalid JSON ({exc.msg})") from exc
    return records


def _normalized(value: str) -> str:
    return " ".join(value.split()).lower()


def _is_av_relevant(classification: dict) -> bool:
    # The pipeline writes this as a bool or as the string "True"/"False".
    value = classification.get("is_av_relevant", True)
    if isinstance(value, str):
        return value.strip().casefold() != "false"
    return bool(value)


def _skills(raw) -> tuple[tuple[str, str, str], ...]:
    if not isinstance(raw, list):
        raise TypeError("skills must be an array")
    skills = {}
    for item in raw:
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("name"), str)
            or not item["name"].strip()
            or item.get("skill_type") not in SKILL_TYPES
        ):
            raise ValueError(f"Invalid skill: {item!r}")
        skills.setdefault((_normalized(item["name"]), item["skill_type"]), item["name"].strip())
    return tuple((name, skill_type, display) for (name, skill_type), display in skills.items())


def _main_type(categories, main_types: dict[str, str]) -> str | None:
    # The enricher already keeps only the dominant main_type's sub_types,
    # so the first recognized one decides it.
    if not isinstance(categories, list) or not all(isinstance(c, str) for c in categories):
        raise TypeError("categories must be an array of strings")
    for category in categories:
        if category in main_types:
            return main_types[category]
    return None


def parse_run(records: list, main_types: dict[str, str] | None = None) -> tuple[list[ClassifiedJob], int]:
    """Returns (AV jobs, rows skipped as not AV-relevant). A malformed row
    rejects the whole run, as the backend imports do."""
    if main_types is None:
        main_types = load_main_types()
    jobs, seen, skipped = [], set(), 0
    for index, row in enumerate(records):
        try:
            if not isinstance(row, dict):
                raise TypeError("Each record must be an object")
            classification = row.get("_classification")
            if not isinstance(classification, dict):
                raise TypeError("_classification must be an object")
            if not _is_av_relevant(classification):
                skipped += 1
                continue
            key = row.get("deduplication_key")
            if not isinstance(key, str) or not _DEDUP_KEY.match(key):
                raise ValueError("deduplication_key must be a 32-character md5 hex string")
            if key in seen:
                raise ValueError("Duplicate deduplication_key in this run")
            seen.add(key)
            title = row.get("job_name")
            if not isinstance(title, str) or not title.strip():
                raise ValueError("job_name must be a non-empty string")
            jobs.append(ClassifiedJob(
                deduplication_key=key,
                title=" ".join(title.split()),
                main_type=_main_type(classification.get("categories") or [], main_types),
                skills=_skills(classification.get("skills") or []),
            ))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Row {index + 1}: {exc}") from exc
    return jobs, skipped


class ClassificationIngest:
    def __init__(self, postgres_config: PostgresConfig | None = None, dbt_config: DbtConfig | None = None):
        self.postgres_config = postgres_config or PostgresConfig()
        self.dbt_config = dbt_config or DbtConfig()

    def ingest(self, jobs: list[ClassifiedJob], *, scraped_at: datetime, source: str = "live",
               classifier_version: str | None = None, completed: bool = True, replace: bool = False) -> dict:
        """One transaction per run. Ingesting an existing scraped_at is a
        no-op unless replace=True, which swaps the run's rows (e.g. after
        re-running the classifier on the same scrape)."""
        if source not in RUN_SOURCES:
            raise ValueError(f"source must be one of {', '.join(RUN_SOURCES)}")
        if scraped_at.tzinfo is None:
            raise ValueError("scraped_at must be timezone-aware")
        connection = psycopg2.connect(self.postgres_config.dsn())
        try:
            with connection, connection.cursor() as cursor:
                cursor.execute(TABLES_SQL)
                if replace:
                    cursor.execute("DELETE FROM silver.classification_run WHERE scraped_at = %s", (scraped_at,))
                cursor.execute(
                    "INSERT INTO silver.classification_run (scraped_at, source, classifier_version, completed, jobs_seen) "
                    "VALUES (%s, %s, %s, %s, %s) ON CONFLICT (scraped_at) DO NOTHING",
                    (scraped_at, source, classifier_version, completed, len(jobs) if completed else 0),
                )
                if cursor.rowcount == 0:
                    return {"status": "already_ingested", "scraped_at": scraped_at.isoformat()}
                if not completed:
                    return {"status": "registered_incomplete", "scraped_at": scraped_at.isoformat()}
                execute_values(
                    cursor,
                    "INSERT INTO silver.classified_job (scraped_at, deduplication_key, job_title, main_type) VALUES %s",
                    [(scraped_at, job.deduplication_key, job.title, job.main_type) for job in jobs],
                )
                skill_rows = [
                    (scraped_at, job.deduplication_key, name, skill_type, display)
                    for job in jobs for name, skill_type, display in job.skills
                ]
                execute_values(
                    cursor,
                    "INSERT INTO silver.classified_job_skill "
                    "(scraped_at, deduplication_key, skill_name, skill_type, display_name) VALUES %s",
                    skill_rows,
                )
        finally:
            connection.close()
        return {
            "status": "replaced" if replace else "ingested",
            "scraped_at": scraped_at.isoformat(),
            "jobs": len(jobs),
            "jobs_without_skills": sum(1 for job in jobs if not job.skills),
            "skill_rows": len(skill_rows),
        }

    def build_gold(self) -> int:
        return self.dbt_config.run("tag:gold", self.postgres_config)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description="Land a scrape run's av_jobs.jsonl in silver and rebuild gold")
    parser.add_argument("input", type=Path, help="The run's av_jobs.jsonl")
    parser.add_argument("--scraped-at", required=True, type=parse_scraped_at,
                        help="When the run scraped, ISO 8601 with a timezone (not the processing time)")
    parser.add_argument("--source", choices=RUN_SOURCES, default="live")
    parser.add_argument("--classifier-version", help="Classifier/prompt/vocabulary version that produced the skills")
    parser.add_argument("--incomplete", action="store_true", help="Register a failed or partial run without its jobs")
    parser.add_argument("--replace", action="store_true", help="Replace a run that was already ingested")
    parser.add_argument("--skip-gold", action="store_true", help="Don't run the gold dbt models afterwards")
    args = parser.parse_args(argv)

    ingest = ClassificationIngest()
    try:
        jobs, skipped = parse_run(read_jsonl(args.input)) if not args.incomplete else ([], 0)
        result = ingest.ingest(
            jobs, scraped_at=args.scraped_at, source=args.source, classifier_version=args.classifier_version,
            completed=not args.incomplete, replace=args.replace,
        )
    except (OSError, TypeError, ValueError, psycopg2.Error) as exc:
        logger.error("Classification ingest failed: %s", exc)
        return 1
    if skipped:
        result["skipped_not_av"] = skipped
    logger.info("Silver classification: %s", json.dumps(result))
    return 0 if args.skip_gold else ingest.build_gold()


if __name__ == "__main__":
    raise SystemExit(main())
