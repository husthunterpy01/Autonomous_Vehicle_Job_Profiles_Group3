from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from scrapers.utils.pipeline_runner import PipelineRunner


@pytest.fixture(autouse=True)
def mock_publish_gold():
    # Stage 9 talks to Postgres (silver ingest, dbt, gold copy); every test
    # here mocks it, and the tests below check how it is called.
    with patch("scrapers.utils.pipeline_runner.publish_pipeline_run", return_value=0) as mock:
        yield mock


def _patch_stage(name, **kwargs):
    return patch(f"scrapers.utils.pipeline_runner.{name}", **kwargs)


def _succeeding_upstream(mock_scraper_runner, mock_silver_ingest, mock_silver_export, mock_prefilter, mock_score):
    mock_scraper_runner.scrape_data_from_sources.return_value = 0
    mock_silver_ingest.return_value.run.return_value = 0
    mock_silver_export.return_value.export.return_value = 5
    mock_prefilter.main.return_value = 0
    mock_score.return_value = 0


@_patch_stage("JobEnricherMain")
@_patch_stage("AVFunctionFilterMain")
@_patch_stage("JobClassifierMain")
@_patch_stage("relevance_classifier_main")
@_patch_stage("JobPrefilterMain")
@_patch_stage("SilverExport")
@_patch_stage("SilverIngest")
@_patch_stage("ScraperRunner")
def test_runs_embedding_then_enricher_and_skips_groq_when_mid_band_empty(
    mock_scraper_runner, mock_silver_ingest, mock_silver_export, mock_prefilter, mock_score, mock_classifier,
    mock_function_filter, mock_enricher, tmp_path,
):
    _succeeding_upstream(mock_scraper_runner, mock_silver_ingest, mock_silver_export, mock_prefilter, mock_score)
    mock_function_filter.main.return_value = 0
    mock_enricher.main.return_value = 0

    # Every other stage is mocked, but PipelineRunner's own
    # _jsonl_has_rows(mid_band_path) check is real disk I/O - point it at an
    # empty tmp dir rather than the (real, gitignored) default data/
    # directory, whose low_confidence_jobs.jsonl may be non-empty from an
    # actual pipeline run elsewhere in this checkout.
    status = PipelineRunner.run(["--classification-output-dir", str(tmp_path / "job_classification")])

    assert status == 0
    mock_score.assert_called_once()
    score_argv = mock_score.call_args.args[0]
    assert score_argv[0] == "score"
    assert "--backend" in score_argv
    assert score_argv[score_argv.index("--backend") + 1] == "embedding"
    assert score_argv[score_argv.index("--low-confidence-low") + 1] == "0.45"
    assert score_argv[score_argv.index("--low-confidence-high") + 1] == "0.55"
    assert score_argv[score_argv.index("--hf-repo-id") + 1] == "husthunterpy01/av-job-relevance-embedding"
    mock_classifier.main.assert_not_called()
    mock_function_filter.main.assert_called_once()
    mock_enricher.main.assert_called_once()

    prefilter_argv = mock_prefilter.main.call_args.args[0]
    prefilter_output_dir = prefilter_argv[prefilter_argv.index("--output-dir") + 1]
    assert score_argv[score_argv.index("--input") + 1] == str(Path(prefilter_output_dir) / "llm_candidates.jsonl")

    classification_dir = Path(score_argv[score_argv.index("--output-dir") + 1])
    function_filter_argv = mock_function_filter.main.call_args.args[0]
    assert function_filter_argv[1] == str(classification_dir / "av_candidates.jsonl")
    assert function_filter_argv[function_filter_argv.index("--output-dir") + 1] == str(classification_dir)

    enricher_argv = mock_enricher.main.call_args.args[0]
    assert enricher_argv[1] == str(classification_dir / "av_engineering_candidates.jsonl")


@_patch_stage("JobEnricherMain")
@_patch_stage("AVFunctionFilterMain")
@_patch_stage("JobClassifierMain")
@_patch_stage("relevance_classifier_main")
@_patch_stage("JobPrefilterMain")
@_patch_stage("SilverExport")
@_patch_stage("SilverIngest")
@_patch_stage("ScraperRunner")
def test_sends_embedding_mid_band_to_groq(
    mock_scraper_runner, mock_silver_ingest, mock_silver_export, mock_prefilter, mock_score, mock_classifier,
    mock_function_filter, mock_enricher, tmp_path,
):
    _succeeding_upstream(mock_scraper_runner, mock_silver_ingest, mock_silver_export, mock_prefilter, mock_score)
    mock_classifier.main.return_value = 0
    mock_function_filter.main.return_value = 0
    mock_enricher.main.return_value = 0
    classification_dir = tmp_path / "job_classification"
    classification_dir.mkdir()
    (classification_dir / "low_confidence_jobs.jsonl").write_text(
        '{"deduplication_key": "mid-band"}\n', encoding="utf-8"
    )

    status = PipelineRunner.run(["--classification-output-dir", str(classification_dir)])

    assert status == 0
    mock_classifier.main.assert_called_once()
    groq_argv = mock_classifier.main.call_args.args[0]
    assert groq_argv[1] == str(classification_dir / "low_confidence_jobs.jsonl")
    assert groq_argv[groq_argv.index("--output-dir") + 1] == str(classification_dir)


@_patch_stage("JobEnricherMain")
@_patch_stage("AVFunctionFilterMain")
@_patch_stage("JobClassifierMain")
@_patch_stage("relevance_classifier_main")
@_patch_stage("JobPrefilterMain")
@_patch_stage("SilverExport")
@_patch_stage("SilverIngest")
@_patch_stage("ScraperRunner")
def test_stops_and_propagates_status_when_scrape_fails(
    mock_scraper_runner, mock_silver_ingest, mock_silver_export, mock_prefilter, mock_score, mock_classifier,
    mock_function_filter, mock_enricher,
):
    mock_scraper_runner.scrape_data_from_sources.return_value = 1

    status = PipelineRunner.run([])

    assert status == 1
    mock_silver_ingest.return_value.run.assert_not_called()
    mock_silver_export.return_value.export.assert_not_called()
    mock_prefilter.main.assert_not_called()
    mock_score.assert_not_called()
    mock_function_filter.main.assert_not_called()


@_patch_stage("JobEnricherMain")
@_patch_stage("AVFunctionFilterMain")
@_patch_stage("JobClassifierMain")
@_patch_stage("relevance_classifier_main")
@_patch_stage("JobPrefilterMain")
@_patch_stage("SilverExport")
@_patch_stage("SilverIngest")
@_patch_stage("ScraperRunner")
def test_stops_when_silver_export_is_empty(
    mock_scraper_runner, mock_silver_ingest, mock_silver_export, mock_prefilter, mock_score, mock_classifier,
    mock_function_filter, mock_enricher,
):
    mock_scraper_runner.scrape_data_from_sources.return_value = 0
    mock_silver_ingest.return_value.run.return_value = 0
    mock_silver_export.return_value.export.return_value = 0

    status = PipelineRunner.run([])

    assert status == 1
    mock_prefilter.main.assert_not_called()
    mock_score.assert_not_called()
    mock_function_filter.main.assert_not_called()


@_patch_stage("JobEnricherMain")
@_patch_stage("AVFunctionFilterMain")
@_patch_stage("JobClassifierMain")
@_patch_stage("relevance_classifier_main")
@_patch_stage("JobPrefilterMain")
@_patch_stage("SilverExport")
@_patch_stage("SilverIngest")
@_patch_stage("ScraperRunner")
def test_skip_flags_bypass_scrape_and_silver_build(
    mock_scraper_runner, mock_silver_ingest, mock_silver_export, mock_prefilter, mock_score, mock_classifier,
    mock_function_filter, mock_enricher, tmp_path,
):
    mock_silver_export.return_value.export.return_value = 5
    mock_prefilter.main.return_value = 0
    mock_score.return_value = 0
    mock_function_filter.main.return_value = 0
    mock_enricher.main.return_value = 0

    # See the matching comment in
    # test_runs_embedding_then_enricher_and_skips_groq_when_mid_band_empty:
    # PipelineRunner's mid-band check is real disk I/O, so this needs an
    # isolated directory rather than the real default data/ one.
    status = PipelineRunner.run(
        ["--skip-scrape", "--skip-silver-build", "--classification-output-dir", str(tmp_path / "job_classification")]
    )

    assert status == 0
    mock_scraper_runner.scrape_data_from_sources.assert_not_called()
    mock_silver_ingest.return_value.run.assert_not_called()
    mock_silver_export.return_value.export.assert_called_once()


@_patch_stage("JobEnricherMain")
@_patch_stage("AVFunctionFilterMain")
@_patch_stage("JobClassifierMain")
@_patch_stage("relevance_classifier_main")
@_patch_stage("JobPrefilterMain")
@_patch_stage("SilverExport")
@_patch_stage("SilverIngest")
@_patch_stage("ScraperRunner")
def test_company_flag_is_passed_through_to_scrape_stage(
    mock_scraper_runner, mock_silver_ingest, mock_silver_export, mock_prefilter, mock_score, mock_classifier,
    mock_function_filter, mock_enricher,
):
    _succeeding_upstream(mock_scraper_runner, mock_silver_ingest, mock_silver_export, mock_prefilter, mock_score)
    mock_function_filter.main.return_value = 0
    mock_enricher.main.return_value = 0

    PipelineRunner.run(["--company", "stack_av"])

    mock_scraper_runner.scrape_data_from_sources.assert_called_once_with(["--company", "stack_av"])


@_patch_stage("JobEnricherMain")
@_patch_stage("AVFunctionFilterMain")
@_patch_stage("JobClassifierMain")
@_patch_stage("relevance_classifier_main")
@_patch_stage("JobPrefilterMain")
@_patch_stage("SilverExport")
@_patch_stage("SilverIngest")
@_patch_stage("ScraperRunner")
def test_stops_when_silver_dbt_build_fails(
    mock_scraper_runner, mock_silver_ingest, mock_silver_export, mock_prefilter, mock_score, mock_classifier,
    mock_function_filter, mock_enricher,
):
    mock_scraper_runner.scrape_data_from_sources.return_value = 0
    mock_silver_ingest.return_value.run.return_value = 1

    status = PipelineRunner.run([])

    assert status == 1
    mock_silver_export.return_value.export.assert_not_called()
    mock_prefilter.main.assert_not_called()
    mock_score.assert_not_called()
    mock_function_filter.main.assert_not_called()


@_patch_stage("JobEnricherMain")
@_patch_stage("AVFunctionFilterMain")
@_patch_stage("JobClassifierMain")
@_patch_stage("relevance_classifier_main")
@_patch_stage("JobPrefilterMain")
@_patch_stage("SilverExport")
@_patch_stage("SilverIngest")
@_patch_stage("ScraperRunner")
def test_stops_and_propagates_status_when_prefilter_fails(
    mock_scraper_runner, mock_silver_ingest, mock_silver_export, mock_prefilter, mock_score, mock_classifier,
    mock_function_filter, mock_enricher,
):
    mock_scraper_runner.scrape_data_from_sources.return_value = 0
    mock_silver_ingest.return_value.run.return_value = 0
    mock_silver_export.return_value.export.return_value = 5
    mock_prefilter.main.return_value = 1

    status = PipelineRunner.run([])

    assert status == 1
    mock_score.assert_not_called()
    mock_classifier.main.assert_not_called()
    mock_function_filter.main.assert_not_called()
    mock_enricher.main.assert_not_called()


@_patch_stage("JobEnricherMain")
@_patch_stage("AVFunctionFilterMain")
@_patch_stage("JobClassifierMain")
@_patch_stage("relevance_classifier_main")
@_patch_stage("JobPrefilterMain")
@_patch_stage("SilverExport")
@_patch_stage("SilverIngest")
@_patch_stage("ScraperRunner")
def test_stops_and_propagates_status_when_relevance_classification_fails(
    mock_scraper_runner, mock_silver_ingest, mock_silver_export, mock_prefilter, mock_score, mock_classifier,
    mock_function_filter, mock_enricher,
):
    mock_scraper_runner.scrape_data_from_sources.return_value = 0
    mock_silver_ingest.return_value.run.return_value = 0
    mock_silver_export.return_value.export.return_value = 5
    mock_prefilter.main.return_value = 0
    mock_score.return_value = 1

    status = PipelineRunner.run([])

    assert status == 1
    mock_classifier.main.assert_not_called()
    mock_function_filter.main.assert_not_called()
    mock_enricher.main.assert_not_called()


@_patch_stage("JobEnricherMain")
@_patch_stage("AVFunctionFilterMain")
@_patch_stage("JobClassifierMain")
@_patch_stage("relevance_classifier_main")
@_patch_stage("JobPrefilterMain")
@_patch_stage("SilverExport")
@_patch_stage("SilverIngest")
@_patch_stage("ScraperRunner")
def test_stops_and_propagates_status_when_function_filter_fails(
    mock_scraper_runner, mock_silver_ingest, mock_silver_export, mock_prefilter, mock_score, mock_classifier,
    mock_function_filter, mock_enricher,
):
    mock_scraper_runner.scrape_data_from_sources.return_value = 0
    mock_silver_ingest.return_value.run.return_value = 0
    mock_silver_export.return_value.export.return_value = 5
    mock_prefilter.main.return_value = 0
    mock_score.return_value = 0
    mock_classifier.main.return_value = 0
    mock_function_filter.main.return_value = 1

    status = PipelineRunner.run([])

    assert status == 1
    mock_enricher.main.assert_not_called()


@_patch_stage("JobEnricherMain")
@_patch_stage("AVFunctionFilterMain")
@_patch_stage("JobClassifierMain")
@_patch_stage("relevance_classifier_main")
@_patch_stage("JobPrefilterMain")
@_patch_stage("SilverExport")
@_patch_stage("SilverIngest")
@_patch_stage("ScraperRunner")
def test_propagates_status_when_enrichment_fails(
    mock_scraper_runner, mock_silver_ingest, mock_silver_export, mock_prefilter, mock_score, mock_classifier,
    mock_function_filter, mock_enricher,
):
    mock_scraper_runner.scrape_data_from_sources.return_value = 0
    mock_silver_ingest.return_value.run.return_value = 0
    mock_silver_export.return_value.export.return_value = 5
    mock_prefilter.main.return_value = 0
    mock_score.return_value = 0
    mock_classifier.main.return_value = 0
    mock_function_filter.main.return_value = 0
    mock_enricher.main.return_value = 1

    status = PipelineRunner.run([])

    assert status == 1


@_patch_stage("JobEnricherMain")
@_patch_stage("AVFunctionFilterMain")
@_patch_stage("JobClassifierMain")
@_patch_stage("relevance_classifier_main")
@_patch_stage("JobPrefilterMain")
@_patch_stage("SilverExport")
@_patch_stage("SilverIngest")
@_patch_stage("ScraperRunner")
def test_prefilter_config_flag_is_passed_through_to_prefilter_stage(
    mock_scraper_runner, mock_silver_ingest, mock_silver_export, mock_prefilter, mock_score, mock_classifier,
    mock_function_filter, mock_enricher,
):
    _succeeding_upstream(mock_scraper_runner, mock_silver_ingest, mock_silver_export, mock_prefilter, mock_score)
    mock_classifier.main.return_value = 0
    mock_function_filter.main.return_value = 0
    mock_enricher.main.return_value = 0

    PipelineRunner.run(["--prefilter-config", "custom_prefilter.yaml"])

    prefilter_argv = mock_prefilter.main.call_args.args[0]
    assert "--config" in prefilter_argv
    assert prefilter_argv[prefilter_argv.index("--config") + 1] == "custom_prefilter.yaml"


@_patch_stage("JobEnricherMain")
@_patch_stage("AVFunctionFilterMain")
@_patch_stage("JobClassifierMain")
@_patch_stage("relevance_classifier_main")
@_patch_stage("JobPrefilterMain")
@_patch_stage("SilverExport")
@_patch_stage("SilverIngest")
@_patch_stage("ScraperRunner")
def test_stage_9_publishes_this_runs_av_jobs_to_gold(
    mock_scraper_runner, mock_silver_ingest, mock_silver_export, mock_prefilter, mock_score, mock_classifier,
    mock_function_filter, mock_enricher, mock_publish_gold, tmp_path,
):
    _succeeding_upstream(mock_scraper_runner, mock_silver_ingest, mock_silver_export, mock_prefilter, mock_score)
    mock_function_filter.main.return_value = 0
    mock_enricher.main.return_value = 0
    classification_dir = tmp_path / "job_classification"
    silver_export = tmp_path / "silver_export.jsonl"

    status = PipelineRunner.run([
        "--classification-output-dir", str(classification_dir),
        "--silver-export-path", str(silver_export),
        "--scraped-at", "2026-09-12T05:46:21Z",
    ])

    assert status == 0
    mock_publish_gold.assert_called_once_with(
        classification_dir / "av_jobs.jsonl", silver_export,
        scraped_at=datetime(2026, 9, 12, 5, 46, 21, tzinfo=timezone.utc),
    )


@_patch_stage("JobEnricherMain")
@_patch_stage("AVFunctionFilterMain")
@_patch_stage("JobClassifierMain")
@_patch_stage("relevance_classifier_main")
@_patch_stage("JobPrefilterMain")
@_patch_stage("SilverExport")
@_patch_stage("SilverIngest")
@_patch_stage("ScraperRunner")
def test_skip_gold_skips_stage_9_and_a_gold_failure_is_propagated(
    mock_scraper_runner, mock_silver_ingest, mock_silver_export, mock_prefilter, mock_score, mock_classifier,
    mock_function_filter, mock_enricher, mock_publish_gold, tmp_path,
):
    _succeeding_upstream(mock_scraper_runner, mock_silver_ingest, mock_silver_export, mock_prefilter, mock_score)
    mock_function_filter.main.return_value = 0
    mock_enricher.main.return_value = 0
    argv = ["--classification-output-dir", str(tmp_path / "job_classification")]

    assert PipelineRunner.run([*argv, "--skip-gold"]) == 0
    mock_publish_gold.assert_not_called()

    mock_publish_gold.return_value = 1
    assert PipelineRunner.run(argv) == 1
    assert mock_publish_gold.call_args.kwargs["scraped_at"] is None
