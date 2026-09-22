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

    @classmethod
    def parse_job_classifier_args(
        cls, argv: list[str] | None = None
    ) -> argparse.Namespace:
        parser = argparse.ArgumentParser(
            description="Screen jobs for AV relevance (stage 1 only; see job_enricher.py for categories/skills)."
        )
        parser.add_argument(
            "--input",
            required=True,
            type=Path,
            help="CSV, JSON, or JSONL (typically job_prefilter's llm_candidates.jsonl)",
        )
        parser.add_argument(
            "--output-dir",
            type=Path,
            default=Path("data") / "job_classification",
            help="Directory for av_candidates.jsonl, non_av_jobs.jsonl, and metrics",
        )
        parser.add_argument(
            "--relevance-batch-size",
            type=int,
            default=20,
            help="Jobs per Groq request in the cheap AV-relevance pass (default: 20)",
        )
        parser.add_argument(
            "--relevance-max-description-chars",
            type=int,
            default=150,
            help=(
                "Fallback excerpt length for the relevance pass, used alongside the "
                "prefilter's already-computed keyword matches rather than the full "
                "description (default: 150)"
            ),
        )
        parser.add_argument(
            "--sample-size",
            type=int,
            default=None,
            help=(
                "Classify only a random sample of this many pending (company, title) "
                "groups instead of all of them - the 'label a seed with the LLM' step "
                "before training relevance_classifier_cli.py on the result."
            ),
        )
        parser.add_argument(
            "--sample-seed",
            type=int,
            default=42,
            help="Random seed for --sample-size, for reproducible seed sets (default: 42)",
        )
        args = parser.parse_args(argv)
        if args.relevance_batch_size < 1:
            parser.error("--relevance-batch-size must be at least 1")
        if args.relevance_max_description_chars < 1:
            parser.error("--relevance-max-description-chars must be at least 1")
        if args.sample_size is not None and args.sample_size < 1:
            parser.error("--sample-size must be at least 1")
        return args

    @classmethod
    def parse_job_enricher_args(
        cls, argv: list[str] | None = None
    ) -> argparse.Namespace:
        parser = argparse.ArgumentParser(
            description="Extract categories and skills for jobs already marked AV-relevant."
        )
        parser.add_argument(
            "--input",
            type=Path,
            default=Path("data") / "job_classification" / "av_candidates.jsonl",
            help="JSONL of AV-relevant jobs, e.g. job_classifier.py's av_candidates.jsonl output",
        )
        parser.add_argument(
            "--output-dir",
            type=Path,
            default=Path("data") / "job_classification",
            help="Directory for av_jobs.jsonl and metrics",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=10,
            help=(
                "Jobs per Groq request (default: 10; the fixed taxonomy prompt is "
                "~850 tokens, so larger batches amortize it further, but pushing "
                "much past 10-15 risks nearing the 8,000 token per-request ceiling)"
            ),
        )
        parser.add_argument(
            "--max-description-chars",
            type=int,
            default=1200,
            help="Description length sent to the enrichment pass (default: 1200)",
        )
        args = parser.parse_args(argv)
        if args.batch_size < 1:
            parser.error("--batch-size must be at least 1")
        if args.max_description_chars < 1:
            parser.error("--max-description-chars must be at least 1")
        return args

    @classmethod
    def parse_pipeline_args(cls, argv: list[str] | None = None) -> argparse.Namespace:
        parser = argparse.ArgumentParser(
            description=(
                "Run the full pipeline end to end: scrape -> MinIO -> bronze -> "
                "Silver (dbt) -> export -> AV pre-filter -> embedding relevance "
                "(Groq only for the mid-band) -> LLM category/skill enrichment."
            )
        )
        parser.add_argument(
            "--company",
            help="Passed through to the scrape stage: run a single company by key",
        )
        parser.add_argument(
            "--skip-scrape",
            action="store_true",
            help="Skip scraping/MinIO/bronze ingest and start from the existing bronze data",
        )
        parser.add_argument(
            "--skip-silver-build",
            action="store_true",
            help="Skip the dbt Silver build and export whatever silver.cleaned_job_postings already has",
        )
        parser.add_argument(
            "--silver-export-path",
            type=Path,
            default=Path("data") / "silver_export.jsonl",
            help="Where to write the Silver export consumed by the pre-filter stage",
        )
        parser.add_argument(
            "--prefilter-output-dir",
            type=Path,
            default=Path("data") / "job_prefilter",
            help="Directory for the pre-filter stage's outputs",
        )
        parser.add_argument(
            "--classification-output-dir",
            type=Path,
            default=Path("data") / "job_classification",
            help="Directory for the relevance and enrichment stages' outputs",
        )
        parser.add_argument(
            "--prefilter-config",
            type=Path,
            default=None,
            help="Optional YAML config for the pre-filter stage (see job_prefilter.py --config)",
        )
        parser.add_argument(
            "--embedding-hf-repo-id",
            default="husthunterpy01/av-job-relevance-embedding",
            help=(
                "Hugging Face repo for the distilled embedding probe when no local "
                "relevance_model_embedding.joblib exists (pass '' to require a local file)"
            ),
        )
        return parser.parse_args(argv)
