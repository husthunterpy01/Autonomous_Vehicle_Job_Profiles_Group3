from __future__ import annotations

import argparse
import logging
from pathlib import Path

import yaml
from scrapers.service.llm.io import JobPostingIO

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_PATH = Path("data") / "job_classification" / "handoff.json"
DEFAULT_MAIN_TYPES_PATH = Path("scrapers") / "config" / "category_main_types.yaml"


def _load_main_types(path: Path | None) -> dict[str, str]:
    if path is None or not path.is_file():
        return {}
    with path.open("r", encoding="utf-8") as stream:
        mapping = yaml.safe_load(stream) or {}
    if not isinstance(mapping, dict):
        raise ValueError(f"{path} must be a YAML mapping of sub_type -> main_type")  # noqa: TRY004 - malformed YAML, not a Python type error
    return mapping


def build_handoff_records(paths: list[Path], main_types_path: Path | None = DEFAULT_MAIN_TYPES_PATH) -> list[dict]:
    """Reshape av_jobs*.jsonl rows into the backend's classification handoff
    contract (see backend/SILVER_SYNC.md): `deduplication_key` +
    `functional_area` (our `categories`, each tagged with its static
    `main_type` from category_main_types.yaml - see
    scrapers/service/llm/category_taxonomy.py for how that mapping was
    derived) + `skills` (already in the `{name, skill_type}` shape
    SilverSync/import_categories expect).

    Later files win on a duplicate deduplication_key, so passing the LLM
    enrichment output after the keyword-resolved one lets a job re-classified
    by the LLM override its keyword-only categories.
    """
    main_types = _load_main_types(main_types_path)
    records: dict[str, dict] = {}
    skipped_uncategorized = 0
    unmapped_categories: set[str] = set()
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
            records[key] = {
                "deduplication_key": key,
                "functional_area": functional_area,
                "skills": classification.get("skills") or [],
            }
    if skipped_uncategorized:
        logger.info("Skipped %d rows with no categories assigned.", skipped_uncategorized)
    if unmapped_categories:
        logger.warning(
            "No main_type mapping for categories %s; leaving main_type unset for those.",
            sorted(unmapped_categories),
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
    args = parser.parse_args(argv)

    records = build_handoff_records(args.input, args.main_types)
    JobPostingIO.write_json(args.output, records)
    logger.info("Wrote %d handoff records to %s.", len(records), args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
