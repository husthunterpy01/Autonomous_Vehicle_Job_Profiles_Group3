from __future__ import annotations

import argparse
import logging
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml
from scrapers.service.llm.io import JobPostingIO
from scrapers.service.silver_cleaning.levels_fyi import fetch_company_average

logger = logging.getLogger(__name__)

DEFAULT_INPUTS = (
    Path("data") / "job_classification" / "av_jobs_keyword_resolved.jsonl",
    Path("data") / "job_classification" / "av_jobs.jsonl",
)
DEFAULT_CACHE_PATH = Path("scrapers") / "data" / "company_salary.yaml"
DEFAULT_MAX_AGE_DAYS = 30
# levels.fyi's own slug doesn't always match our scraped company_name (casing,
# punctuation, legal suffixes, outright different naming) - override the
# handful of known mismatches rather than guessing.
SLUG_OVERRIDES = {
    "gm": "general-motors",
    "xpeng": "xpeng-motors",
}


def _slugify(company_name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", company_name.lower()).strip("-")
    return SLUG_OVERRIDES.get(slug, slug)


def _company_names(paths: list[Path]) -> list[str]:
    names: dict[str, None] = {}  # dict for order-preserving de-dup
    for path in paths:
        if not path.is_file():
            continue
        for row in JobPostingIO.load(path):
            name = row.get("company_name")
            if isinstance(name, str) and name.strip():
                names.setdefault(name.strip(), None)
    return list(names)


def _load_cache(path: Path) -> dict:
    if not path.is_file():
        return {}
    with path.open("r", encoding="utf-8") as stream:
        return yaml.safe_load(stream) or {}


def _is_fresh(entry: dict, max_age_days: int) -> bool:
    fetched_at = entry.get("fetched_at")
    if not fetched_at:
        return False
    try:
        fetched = datetime.fromisoformat(fetched_at)
    except ValueError:
        return False
    return datetime.now(timezone.utc) - fetched <= timedelta(days=max_age_days)


def refresh(
    company_names: list[str],
    cache_path: Path,
    *,
    max_age_days: int = DEFAULT_MAX_AGE_DAYS,
    force: bool = False,
    pause_seconds: float = 1.0,
) -> dict:
    cache = _load_cache(cache_path)
    fetched = skipped = missing = errored = 0

    try:
        for company_name in company_names:
            entry = cache.get(company_name)
            if entry and not force and _is_fresh(entry, max_age_days):
                skipped += 1
                continue

            slug = _slugify(company_name)
            try:
                average = fetch_company_average(slug)
            except Exception as exc:  # noqa: BLE001 - best-effort fallback; a single company's fetch
                # failure (429/403/5xx/timeout - fetch_company_average only
                # swallows 404s and connection errors itself) must not lose
                # every company already fetched earlier in this run.
                logger.warning("Failed to fetch levels.fyi data for %s (slug=%s): %s", company_name, slug, exc)
                errored += 1
                time.sleep(pause_seconds)
                continue
            if average is None:
                logger.info("No levels.fyi data for %s (slug=%s).", company_name, slug)
                missing += 1
                time.sleep(pause_seconds)
                continue

            cache[company_name] = {
                "avg_total_comp": average.median_total_compensation,
                "currency": average.currency,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "levels_fyi_url": average.source_url,
            }
            fetched += 1
            logger.info(
                "%s -> %s %s (levels.fyi median total comp)",
                company_name, average.median_total_compensation, average.currency,
            )
            time.sleep(pause_seconds)
    finally:
        # Write whatever was fetched even if the loop above raised something
        # unanticipated (the per-company try/except covers known failure
        # modes; this is the last line of defense for the rest) - a run
        # that gets 90% through must not throw away that 90%.
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with cache_path.open("w", encoding="utf-8") as stream:
            yaml.safe_dump(cache, stream, sort_keys=True, allow_unicode=True)

    logger.info("Fetched %d, skipped %d (fresh), missing %d, errored %d.", fetched, skipped, missing, errored)
    return cache


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    parser = argparse.ArgumentParser(
        description=(
            "Refresh the levels.fyi average-compensation cache "
            "(scrapers/data/company_salary.yaml) for companies appearing in "
            "the AV job outputs. Occasional/manual command - not part of "
            "pipeline_main.py's automatic chain, since this data barely changes."
        )
    )
    parser.add_argument(
        "--input", action="append", type=Path,
        help="An av_jobs*.jsonl file to pull company names from; repeatable. Defaults to both known output files.",
    )
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE_PATH)
    parser.add_argument(
        "--max-age-days", type=int, default=DEFAULT_MAX_AGE_DAYS,
        help="Skip a company already cached within this many days (default: 30)",
    )
    parser.add_argument("--force", action="store_true", help="Refetch even fresh cache entries")
    parser.add_argument("--pause-seconds", type=float, default=1.0)
    args = parser.parse_args(argv)

    inputs = args.input or list(DEFAULT_INPUTS)
    company_names = _company_names(inputs)
    logger.info("Found %d distinct companies across %d input file(s).", len(company_names), len(inputs))

    refresh(
        company_names,
        args.cache,
        max_age_days=args.max_age_days,
        force=args.force,
        pause_seconds=args.pause_seconds,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
