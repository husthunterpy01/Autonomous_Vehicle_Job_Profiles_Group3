from __future__ import annotations

import logging
import sys
from pathlib import Path

from scrapers.service.silver_cleaning.silver_export import SilverExport
from scrapers.service.silver_cleaning.silver_ingest import SilverIngest
from scrapers.utils.job_classifier import JobClassifierMain
from scrapers.utils.job_enricher import JobEnricherMain
from scrapers.utils.job_prefilter import JobPrefilterMain
from scrapers.utils.parser import ScraperParser
from scrapers.utils.relevance_classifier_cli import main as relevance_classifier_main
from scrapers.utils.runner import ScraperRunner

logger = logging.getLogger(__name__)

# Tight gates: only the true middle band goes to Groq. Confident AV/non-AV
# stay on the local probe (see scrapers/data/snapshots/).
_EMBEDDING_LOW_CONFIDENCE_LOW = "0.45"
_EMBEDDING_LOW_CONFIDENCE_HIGH = "0.55"


def _jsonl_has_rows(path: Path) -> bool:
    if not path.is_file():
        return False
    with path.open(encoding="utf-8") as stream:
        return any(line.strip() for line in stream)


class PipelineRunner:
    """Chains the whole pipeline: scrape -> MinIO -> bronze -> Silver (dbt)
    -> export -> AV pre-filter -> distilled embedding relevance -> Groq
    mid-band -> LLM category/skill enrichment.

    Each stage is an existing, independently testable CLI entrypoint; this
    just sequences them in-process and stops at the first failure, so a bad
    stage doesn't silently feed corrupt or partial input to the next one.
    --skip-scrape and --skip-silver-build let a rerun start partway through
    (e.g. re-running just the LLM stages against data already in Postgres).
    """

    @classmethod
    def run(cls, argv: list[str] | None = None) -> int:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
            stream=sys.stderr,
        )
        args = ScraperParser.parse_pipeline_args(argv)

        if not args.skip_scrape:
            logger.info("Stage 1/7: scraping sources -> MinIO -> bronze.")
            status = ScraperRunner.scrape_data_from_sources(
                ["--company", args.company] if args.company else []
            )
            if status:
                logger.error("Scrape stage failed; stopping pipeline.")
                return status
        else:
            logger.info("Stage 1/7: skipped (--skip-scrape).")

        if not args.skip_silver_build:
            logger.info("Stage 2/7: building the dbt Silver model.")
            status = SilverIngest().run()
            if status:
                logger.error("Silver dbt build failed; stopping pipeline.")
                return status
        else:
            logger.info("Stage 2/7: skipped (--skip-silver-build).")

        logger.info("Stage 3/7: exporting Silver rows to %s.", args.silver_export_path)
        row_count = SilverExport().export(args.silver_export_path)
        if row_count == 0:
            logger.error("Silver export produced no rows; stopping pipeline.")
            return 1

        logger.info("Stage 4/7: AV pre-filter.")
        prefilter_argv = [
            "--input", str(args.silver_export_path),
            "--output-dir", str(args.prefilter_output_dir),
        ]
        if args.prefilter_config:
            prefilter_argv += ["--config", str(args.prefilter_config)]
        status = JobPrefilterMain.main(prefilter_argv)
        if status:
            logger.error("Pre-filter stage failed; stopping pipeline.")
            return status

        classification_dir = args.classification_output_dir
        logger.info("Stage 5/7: distilled embedding AV-relevance scoring.")
        score_argv = [
            "score",
            "--input", str(args.prefilter_output_dir / "llm_candidates.jsonl"),
            "--output-dir", str(classification_dir),
            "--backend", "embedding",
            "--low-confidence-low", _EMBEDDING_LOW_CONFIDENCE_LOW,
            "--low-confidence-high", _EMBEDDING_LOW_CONFIDENCE_HIGH,
        ]
        if args.embedding_hf_repo_id is not None:
            score_argv += ["--hf-repo-id", args.embedding_hf_repo_id]
        status = relevance_classifier_main(score_argv)
        if status:
            logger.error("Embedding relevance stage failed; stopping pipeline.")
            return status

        mid_band_path = classification_dir / "low_confidence_jobs.jsonl"
        if _jsonl_has_rows(mid_band_path):
            logger.info("Stage 6/7: Groq AV-relevance for embedding mid-band.")
            status = JobClassifierMain.main(
                [
                    "--input", str(mid_band_path),
                    "--output-dir", str(classification_dir),
                ]
            )
            if status:
                logger.error("Groq mid-band relevance stage failed; stopping pipeline.")
                return status
        else:
            logger.info("Stage 6/7: skipped (no embedding mid-band rows).")

        logger.info("Stage 7/7: LLM category/skill enrichment.")
        status = JobEnricherMain.main(
            [
                "--input", str(classification_dir / "av_candidates.jsonl"),
                "--output-dir", str(classification_dir),
            ]
        )
        if status:
            logger.error("Enrichment stage failed; stopping pipeline.")
            return status

        logger.info(
            "Pipeline complete. Final Silver-layer AV jobs: %s",
            classification_dir / "av_jobs.jsonl",
        )
        return 0
