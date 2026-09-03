from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from scrapers.service.job_prefilter import JobPrefilter, load_postings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Filter bronze job postings before sending them to an LLM."
    )
    parser.add_argument(
        "--input", required=True, type=Path, help="CSV, JSON, or JSONL"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data") / "job_prefilter",
        help="Directory for candidates, excluded audit rows, and metrics",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help=(
            "Optional YAML config; defaults to AV_JOB_PREFILTER_CONFIG "
            "or repository config"
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    result = JobPrefilter.from_config(args.config).filter(load_postings(args.input))
    paths = result.write_outputs(args.output_dir)
    print(
        json.dumps(
            {
                "before_count": result.before_count,
                "after_count": result.after_count,
                "excluded_count": len(result.excluded),
                "outputs": {name: str(path) for name, path in paths.items()},
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
