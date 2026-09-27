"""Manual command: python -m app.load_gold av_jobs.jsonl --scraped-at 2026-08-31T12:00:00Z.

Loads one scrape run into the gold star schema (DOC-13). Run it after
import_skills; needs doc13_skill_trend_migration.sql applied.
"""
import argparse
from pathlib import Path

from app.core.database import engine
from app.services.gold_loader import (
    RUN_SOURCES,
    GoldLoader,
    parse_run,
    parse_scraped_at,
    read_jsonl,
)
from app.utils.cli import run_command


def main():
    parser = argparse.ArgumentParser(description="Load one scrape run's av_jobs.jsonl into the gold skill trend tables")
    parser.add_argument("input", type=Path, help="Path to the run's av_jobs.jsonl")
    parser.add_argument("--scraped-at", required=True, type=parse_scraped_at,
                        help="When the run scraped, ISO 8601 with a timezone (not the processing time)")
    parser.add_argument("--source", choices=RUN_SOURCES, default="live")
    parser.add_argument("--classifier-version", help="Classifier/prompt version that produced the skills")
    parser.add_argument("--incomplete", action="store_true",
                        help="Register a failed or partial run without writing any facts")

    def load(args):
        jobs, skipped = parse_run(read_jsonl(args.input))
        result = GoldLoader(engine).load(
            jobs, scraped_at=args.scraped_at, source=args.source,
            classifier_version=args.classifier_version, completed=not args.incomplete,
        )
        if skipped:
            result["skipped_not_av"] = skipped
        return result

    run_command(parser, load)


if __name__ == "__main__":
    main()
