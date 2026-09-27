"""DOC-13: load one scrape run's pipeline output into the gold star schema.

Reads the run's av_jobs.jsonl (every line is an AV job with its
deduplication_key, job_name and _classification), not the backend tables,
so re-importing jobs never touches gold. See document/gold-trend-mart/README.md.
"""
import json
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

from sqlalchemy import text

from app.services.category_sync import _MAIN_TYPES_BY_NORMALIZED_NAME
from app.services.skill_sync import _validate_skills

RUN_SOURCES = ("live", "backfill")
_DEDUP_KEY = re.compile(r"^[0-9a-f]{32}$")
_SCHEMA_NAME = re.compile(r"^[a-z_][a-z0-9_]*$")
# Separate from the backend import lock (80009001): gold loads only
# serialize with each other.
_GOLD_WRITER_LOCK = 80009013
# Not strftime("%b"), which follows the process locale.
_MONTH_ABBR = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


@dataclass(frozen=True)
class GoldJob:
    deduplication_key: str
    title: str
    main_type: str | None
    skills: tuple[tuple[str, str, str], ...]  # (normalized_name, skill_type, display_name)


def parse_scraped_at(value: str) -> datetime:
    """ISO 8601 with a timezone; "Z" is accepted for UTC."""
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"scraped_at is not an ISO 8601 timestamp: {value!r}") from exc
    if parsed.tzinfo is None:
        raise ValueError("scraped_at must include a timezone, e.g. 2026-08-31T12:00:00Z")
    return parsed


def read_jsonl(path: Path) -> list[dict]:
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


def _is_av_relevant(classification: dict) -> bool:
    # The pipeline writes this as a bool or as the string "True"/"False".
    value = classification.get("is_av_relevant", True)
    if isinstance(value, str):
        return value.strip().casefold() != "false"
    return bool(value)


def _main_type(categories) -> str | None:
    """The job's one main_type, as the backend shows it: the main_type with
    the most sub_types, ties going to the one listed first."""
    if isinstance(categories, str):
        categories = [categories]
    if not isinstance(categories, list):
        raise TypeError("categories must be an array of strings")
    main_types = []
    for label in categories:
        if not isinstance(label, str):
            raise TypeError("Category labels must be strings")
        key = " ".join(unicodedata.normalize("NFKC", label).split()).casefold()
        main_type = _MAIN_TYPES_BY_NORMALIZED_NAME.get(key)
        if main_type is not None:
            main_types.append(main_type)
    if not main_types:
        return None
    counts = Counter(main_types)
    return max(main_types, key=lambda main_type: (counts[main_type], -main_types.index(main_type)))


def parse_run(records: list) -> tuple[list[GoldJob], int]:
    """Returns (AV jobs, number of rows skipped as not AV-relevant).

    Rejects the whole run on a malformed row, as the other imports do."""
    if not isinstance(records, list):
        raise TypeError("Run output must be a list of job records")
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
            skills = {}
            for norm_name, skill_type, display_name in _validate_skills(classification.get("skills") or []):
                skills.setdefault((norm_name, skill_type), display_name)
            jobs.append(GoldJob(
                deduplication_key=key,
                title=" ".join(title.split()),
                main_type=_main_type(classification.get("categories") or []),
                skills=tuple((name, skill_type, display) for (name, skill_type), display in skills.items()),
            ))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Row {index + 1}: {exc}") from exc
    return jobs, skipped


class GoldLoader:
    """Loads a run in one transaction; reloading the same scraped_at is a no-op."""

    def __init__(self, engine, schema: str = "gold"):
        if not _SCHEMA_NAME.match(schema):
            raise ValueError("Invalid gold schema name")
        self.engine = engine
        self.schema = schema

    def load(self, jobs: list[GoldJob], *, scraped_at: datetime, source: str,
             classifier_version: str | None = None, completed: bool = True) -> dict:
        if source not in RUN_SOURCES:
            raise ValueError(f"source must be one of {', '.join(RUN_SOURCES)}")
        if scraped_at.tzinfo is None:
            raise ValueError("scraped_at must be timezone-aware")
        g = f'"{self.schema}"'
        with self.engine.begin() as conn:
            conn.execute(text("SELECT pg_advisory_xact_lock(:lock)"), {"lock": _GOLD_WRITER_LOCK})
            run_id = conn.execute(text(f"""
                INSERT INTO {g}.scrape_run (scraped_at, source, classifier_version, jobs_seen)
                VALUES (:scraped_at, :source, :classifier_version, :jobs_seen)
                ON CONFLICT (scraped_at) DO NOTHING
                RETURNING run_id
            """), {"scraped_at": scraped_at, "source": source,
                   "classifier_version": classifier_version, "jobs_seen": len(jobs)}).scalar()
            if run_id is None:
                return {"status": "already_loaded", "scraped_at": scraped_at.isoformat()}
            if not completed:
                return {"status": "registered_incomplete", "run_id": str(run_id)}

            # Calendar month in UTC (README decision 3).
            utc = scraped_at.astimezone(timezone.utc)
            month_key = utc.year * 100 + utc.month
            conn.execute(text(f"""
                INSERT INTO {g}.dim_month (month_key, month_start, year, month, label)
                VALUES (:month_key, :month_start, :year, :month, :label)
                ON CONFLICT (month_key) DO NOTHING
            """), {"month_key": month_key, "month_start": date(utc.year, utc.month, 1),
                   "year": utc.year, "month": utc.month, "label": f"{_MONTH_ABBR[utc.month - 1]} {utc.year}"})

            job_keys = dict(conn.execute(text(f"""
                INSERT INTO {g}.dim_job (deduplication_key, title, main_type, first_seen_at, last_seen_at)
                SELECT k, t, m, :scraped_at, :scraped_at
                FROM unnest(CAST(:keys AS text[]), CAST(:titles AS text[]), CAST(:main_types AS text[])) AS j(k, t, m)
                ON CONFLICT (deduplication_key) DO UPDATE SET
                    title = CASE WHEN excluded.last_seen_at >= {g}.dim_job.last_seen_at
                                 THEN excluded.title ELSE {g}.dim_job.title END,
                    main_type = CASE WHEN excluded.last_seen_at >= {g}.dim_job.last_seen_at
                                     THEN excluded.main_type ELSE {g}.dim_job.main_type END,
                    first_seen_at = least({g}.dim_job.first_seen_at, excluded.first_seen_at),
                    last_seen_at = greatest({g}.dim_job.last_seen_at, excluded.last_seen_at)
                RETURNING deduplication_key, job_key
            """), {"scraped_at": scraped_at,
                   "keys": [job.deduplication_key for job in jobs],
                   "titles": [job.title for job in jobs],
                   "main_types": [job.main_type for job in jobs]}).all())

            distinct_skills = {}
            for job in jobs:
                for norm_name, skill_type, display_name in job.skills:
                    distinct_skills.setdefault((norm_name, skill_type), display_name)
            skill_keys = {
                (name, skill_type): key
                for name, skill_type, key in conn.execute(text(f"""
                    INSERT INTO {g}.dim_skill (normalized_name, skill_type, display_name)
                    SELECT n, t, d
                    FROM unnest(CAST(:names AS text[]), CAST(:types AS text[]), CAST(:displays AS text[])) AS s(n, t, d)
                    ON CONFLICT (normalized_name, skill_type) DO UPDATE SET display_name = excluded.display_name
                    RETURNING normalized_name, skill_type, skill_key
                """), {"names": [name for name, _ in distinct_skills],
                       "types": [skill_type for _, skill_type in distinct_skills],
                       "displays": list(distinct_skills.values())})
            }

            fact_jobs, fact_skills = [], []
            for job in jobs:
                for norm_name, skill_type, _ in job.skills:
                    fact_jobs.append(job_keys[job.deduplication_key])
                    fact_skills.append(skill_keys[(norm_name, skill_type)])
            conn.execute(text(f"""
                INSERT INTO {g}.fact_job_skill_month (month_key, job_key, skill_key, first_seen_at, last_seen_at)
                SELECT :month_key, j, s, :scraped_at, :scraped_at
                FROM unnest(CAST(:job_keys AS bigint[]), CAST(:skill_keys AS bigint[])) AS f(j, s)
                ON CONFLICT (month_key, job_key, skill_key) DO UPDATE SET
                    first_seen_at = least({g}.fact_job_skill_month.first_seen_at, excluded.first_seen_at),
                    last_seen_at = greatest({g}.fact_job_skill_month.last_seen_at, excluded.last_seen_at)
            """), {"month_key": month_key, "scraped_at": scraped_at,
                   "job_keys": fact_jobs, "skill_keys": fact_skills})

            conn.execute(text(f"UPDATE {g}.scrape_run SET completed = true WHERE run_id = :run_id"),
                         {"run_id": run_id})
        return {
            "status": "loaded",
            "run_id": str(run_id),
            "month_key": month_key,
            "jobs": len(jobs),
            "jobs_without_skills": sum(1 for job in jobs if not job.skills),
            "skills": len(distinct_skills),
            "facts": len(fact_jobs),
        }
