from __future__ import annotations

import argparse
import logging
from pathlib import Path

import yaml

from scrapers.service.llm.io import JobPostingIO
from scrapers.service.silver_cleaning.salary_extractor import extract_salary_from_text

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_PATH = Path("data") / "job_classification" / "handoff.json"
DEFAULT_MAIN_TYPES_PATH = Path("scrapers") / "config" / "category_main_types.yaml"
DEFAULT_COMPANY_SALARY_CACHE_PATH = Path("scrapers") / "data" / "company_salary.yaml"


def _load_main_types(path: Path | None) -> dict[str, str]:
    if path is None or not path.is_file():
        return {}
    with path.open("r", encoding="utf-8") as stream:
        mapping = yaml.safe_load(stream) or {}
    if not isinstance(mapping, dict):
        raise ValueError(f"{path} must be a YAML mapping of sub_type -> main_type")
    return mapping


def _load_company_salary_cache(path: Path | None) -> dict[str, dict]:
    if path is None or not path.is_file():
        return {}
    with path.open("r", encoding="utf-8") as stream:
        cache = yaml.safe_load(stream) or {}
    if not isinstance(cache, dict):
        raise ValueError(f"{path} must be a YAML mapping of company_name -> cache entry")
    return cache


def _salary_fields(row: dict, company_salary_cache: dict[str, dict]) -> dict:
    """Priority order: Phase 1 (structured API field, survived from Silver)
    -> Phase 2a (regex on the original description) -> Phase 2b (levels.fyi
    company average, tagged as such) -> nothing (no keys added; the backend
    leaves salary null, same as today - never invents a number)."""
    if row.get("salary_min") is not None and row.get("salary_max") is not None:
        return {
            "salary_min": row["salary_min"],
            "salary_max": row["salary_max"],
            "salary_currency": row.get("salary_currency"),
            "salary_period": row.get("salary_period"),
            "salary_source": "api",
        }

    estimate = extract_salary_from_text(row.get("job_description") or "")
    if estimate is not None:
        return {
            "salary_min": estimate.min,
            "salary_max": estimate.max,
            "salary_currency": estimate.currency,
            "salary_period": estimate.period,
            "salary_source": "regex",
        }

    cached = company_salary_cache.get(row.get("company_name") or "")
    if cached is not None:
        average = cached.get("avg_total_comp")
        if average is not None:
            return {
                "salary_min": average,
                "salary_max": average,
                "salary_currency": cached.get("currency"),
                "salary_period": "yearly",
                "salary_source": "levels_fyi_average",
            }

    return {}


def build_handoff_records(
    paths: list[Path],
    main_types_path: Path | None = DEFAULT_MAIN_TYPES_PATH,
    company_salary_cache_path: Path | None = DEFAULT_COMPANY_SALARY_CACHE_PATH,
) -> list[dict]:
    """Reshape av_jobs*.jsonl rows into the backend's classification handoff
    contract (see backend/SILVER_SYNC.md): `deduplication_key` +
    `functional_area` (our `categories`, each tagged with its static
    `main_type` from category_main_types.yaml - see
    scrapers/service/llm/category_taxonomy.py for how that mapping was
    derived) + `skills` (already in the `{name, skill_type}` shape
    SilverSync/import_categories expect) + salary fields (see
    `_salary_fields` for the source priority).

    Later files win on a duplicate deduplication_key, so passing the LLM
    enrichment output after the keyword-resolved one lets a job re-classified
    by the LLM override its keyword-only categories.
    """
    main_types = _load_main_types(main_types_path)
    company_salary_cache = _load_company_salary_cache(company_salary_cache_path)
    records: dict[str, dict] = {}
    skipped_uncategorized = 0
    unmapped_categories: set[str] = set()
    salary_source_counts: dict[str, int] = {}
    for path in paths:
        for row in JobPostingIO.load(path):
            key = row.get("deduplication_key")
            if not key:
                continue
            classification = row.get("_classification") or {}
            categories = classification.get("categories") or []
            if not categories:
                skipped_uncategorized += 1
                continue
            functional_area = []
            for category in categories:
                main_type = main_types.get(category)
                if main_type is None:
                    unmapped_categories.add(category)
                functional_area.append({"sub_type": category, "main_type": main_type})
            salary_fields = _salary_fields(row, company_salary_cache)
            if salary_fields:
                salary_source_counts[salary_fields["salary_source"]] = (
                    salary_source_counts.get(salary_fields["salary_source"], 0) + 1
                )
            records[key] = {
                "deduplication_key": key,
                "functional_area": functional_area,
                "skills": classification.get("skills") or [],
                **salary_fields,
            }
    if skipped_uncategorized:
        logger.info("Skipped %d rows with no categories assigned.", skipped_uncategorized)
    if unmapped_categories:
        logger.warning(
            "No main_type mapping for categories %s; leaving main_type unset for those.",
            sorted(unmapped_categories),
        )
    logger.info(
        "Salary resolved for %d/%d records (%s).",
        sum(salary_source_counts.values()), len(records), salary_source_counts,
    )
    return list(records.values())


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    parser = argparse.ArgumentParser(
        description=(
            "Build a classification handoff JSON array from one or more "
            "av_jobs*.jsonl files, for backend/app/validate_handoff.py and "
            "app/import_categories.py."
        )
    )
    parser.add_argument(
        "--input",
        action="append",
        required=True,
        type=Path,
        help="An av_jobs*.jsonl file; pass more than once to merge several",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument(
        "--main-types",
        type=Path,
        default=DEFAULT_MAIN_TYPES_PATH,
        help="YAML mapping of sub_type -> main_type; pass a missing/empty path to skip",
    )
    parser.add_argument(
        "--company-salary-cache",
        type=Path,
        default=DEFAULT_COMPANY_SALARY_CACHE_PATH,
        help="YAML cache from refresh_company_salary_cache.py; pass a missing/empty path to skip",
    )
    args = parser.parse_args(argv)

    records = build_handoff_records(args.input, args.main_types, args.company_salary_cache)
    JobPostingIO.write_json(args.output, records)
    logger.info("Wrote %d handoff records to %s.", len(records), args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
