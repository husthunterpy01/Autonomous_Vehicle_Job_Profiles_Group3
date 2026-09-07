from __future__ import annotations

import argparse
from pathlib import Path


class ScraperParser:
    @classmethod
    def build_common_parser( cls, description: str, default_output: Path) -> argparse.ArgumentParser:
        """Create the CLI arguments shared by every company scraper."""

        parser = argparse.ArgumentParser(description=description)
        parser.add_argument(
            "--output",
            type=Path,
            default=default_output,
            help=f"JSON output path (default: {default_output})",
        )
        parser.add_argument(
            "--timeout",
            type=float,
            default=30.0,
            help="HTTP timeout in seconds (default: 30)",
        )
        return parser

    @classmethod
    def validate_common_args(
        cls, parser: argparse.ArgumentParser, args: argparse.Namespace
    ) -> argparse.Namespace:
        """Apply shared command-line validation."""

        if args.timeout <= 0:
            parser.error("--timeout must be greater than 0")
        return args

    @classmethod
    def parse_args(cls, argv: list[str] | None = None) -> argparse.Namespace:
        parser = argparse.ArgumentParser(
            description="Fetch public ATS job payloads and archive them to MinIO."
        )
        parser.add_argument(
            "--company",
            help="Run a single company by key from list_companies.yaml (for example stack_av)",
        )
        parser.add_argument(
            "--timeout",
            type=float,
            default=30.0,
            help="HTTP timeout in seconds (default: 30)",
        )
        parser.add_argument(
            "--max-jobs",
            type=int,
            default=100,
            help="Maximum jobs to keep from each company response (default: 100)",
        )
        args = parser.parse_args(argv)
        if args.timeout <= 0:
            parser.error("--timeout must be greater than 0")
        if args.max_jobs < 1:
            parser.error("--max-jobs must be at least 1")
        return args

    @classmethod
    def parse_job_prefilter_args(
        cls, argv: list[str] | None = None
    ) -> argparse.Namespace:
        parser = argparse.ArgumentParser(
            description="Filter Bronze/Silver jobs before sending them to an LLM."
        )
        parser.add_argument(
            "--input", required=True, type=Path, help="CSV, JSON, or JSONL"
        )
        parser.add_argument(
            "--output-dir",
            type=Path,
            default=Path("data") / "job_prefilter",
            help="Directory for candidates, audit rows, metrics, and decision CSV",
        )
        parser.add_argument(
            "--config",
            type=Path,
            default=None,
            help=(
                "Optional YAML config; defaults to AV_JOB_PREFILTER_CONFIG "
                "or scrapers/config/job_prefilter.yaml"
            ),
        )
        return parser.parse_args(argv)
