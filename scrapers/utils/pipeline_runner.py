from __future__ import annotations

import logging
import sys

from scrapers.service.silver_cleaning.silver_export import SilverExport
from scrapers.service.silver_cleaning.silver_ingest import SilverIngest
from scrapers.utils.job_classifier import JobClassifierMain
from scrapers.utils.job_enricher import JobEnricherMain
from scrapers.utils.job_prefilter import JobPrefilterMain
from scrapers.utils.parser import ScraperParser
from scrapers.utils.runner import ScraperRunner

logger = logging.getLogger(__name__)


class PipelineRunner:
    """Chains the whole pipeline: scrape -> MinIO -> bronze -> Silver (dbt)
    -> export -> AV pre-filter -> LLM relevance -> LLM category/skill
    enrichment, producing the final Silver-layer AV jobs file.

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
            logger.info("Stage 1/6: scraping sources -> MinIO -> bronze.")
            status = ScraperRunner.scrape_data_from_sources(
                ["--company", args.company] if args.company else []
            )
            if status:
                logger.error("Scrape stage failed; stopping pipeline.")
                return status
        else:
            logger.info("Stage 1/6: skipped (--skip-scrape).")

        if not args.skip_silver_build:
            logger.info("Stage 2/6: building the dbt Silver model.")
            status = SilverIngest().run()
            if status:
                logger.error("Silver dbt build failed; stopping pipeline.")
                return status
        else:
            logger.info("Stage 2/6: skipped (--skip-silver-build).")

        logger.info("Stage 3/6: exporting Silver rows to %s.", args.silver_export_path)
        row_count = SilverExport().export(args.silver_export_path)
        if row_count == 0:
            logger.error("Silver export produced no rows; stopping pipeline.")
            return 1

        logger.info("Stage 4/6: AV pre-filter.")
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

        logger.info("Stage 5/6: LLM AV-relevance classification.")
        status = JobClassifierMain.main(
            [
                "--input", str(args.prefilter_output_dir / "llm_candidates.jsonl"),
                "--output-dir", str(args.classification_output_dir),
            ]
        )
        if status:
            logger.error("Relevance classification stage failed; stopping pipeline.")
            return status

        logger.info("Stage 6/6: LLM category/skill enrichment.")
        status = JobEnricherMain.main(
            [
                "--input", str(args.classification_output_dir / "av_candidates.jsonl"),
                "--output-dir", str(args.classification_output_dir),
            ]
        )
        if status:
            logger.error("Enrichment stage failed; stopping pipeline.")
            return status

        logger.info(
            "Pipeline complete. Final Silver-layer AV jobs: %s",
            args.classification_output_dir / "av_jobs.jsonl",
        )
        return 0
