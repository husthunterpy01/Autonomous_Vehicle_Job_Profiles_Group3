from pathlib import Path
from unittest.mock import patch

from scrapers.utils.pipeline_runner import PipelineRunner


def _patch_stage(name, **kwargs):
    return patch(f"scrapers.utils.pipeline_runner.{name}", **kwargs)


@_patch_stage("JobEnricherMain")
@_patch_stage("JobClassifierMain")
@_patch_stage("JobPrefilterMain")
@_patch_stage("SilverExport")
@_patch_stage("SilverIngest")
@_patch_stage("ScraperRunner")
def test_runs_every_stage_in_order_on_success(
    mock_scraper_runner, mock_silver_ingest, mock_silver_export, mock_prefilter, mock_classifier, mock_enricher
):
    mock_scraper_runner.scrape_data_from_sources.return_value = 0
    mock_silver_ingest.return_value.run.return_value = 0
    mock_silver_export.return_value.export.return_value = 5
    mock_prefilter.main.return_value = 0
    mock_classifier.main.return_value = 0
    mock_enricher.main.return_value = 0

    status = PipelineRunner.run([])

    assert status == 0
    mock_scraper_runner.scrape_data_from_sources.assert_called_once_with([])
    mock_silver_ingest.return_value.run.assert_called_once()
    mock_silver_export.return_value.export.assert_called_once()
    mock_prefilter.main.assert_called_once()
    mock_classifier.main.assert_called_once()
    mock_enricher.main.assert_called_once()

    # each stage's input matches the previous stage's declared output
    prefilter_argv = mock_prefilter.main.call_args.args[0]
    assert "--output-dir" in prefilter_argv
    prefilter_output_dir = prefilter_argv[prefilter_argv.index("--output-dir") + 1]

    classifier_argv = mock_classifier.main.call_args.args[0]
    # Path-joined with pathlib (not a literal "/") so this matches on Windows too.
    assert classifier_argv[1] == str(Path(prefilter_output_dir) / "llm_candidates.jsonl")
    classifier_output_dir = classifier_argv[classifier_argv.index("--output-dir") + 1]

    enricher_argv = mock_enricher.main.call_args.args[0]
    assert enricher_argv[1] == str(Path(classifier_output_dir) / "av_candidates.jsonl")


@_patch_stage("JobEnricherMain")
@_patch_stage("JobClassifierMain")
@_patch_stage("JobPrefilterMain")
@_patch_stage("SilverExport")
@_patch_stage("SilverIngest")
@_patch_stage("ScraperRunner")
def test_stops_and_propagates_status_when_scrape_fails(
    mock_scraper_runner, mock_silver_ingest, mock_silver_export, mock_prefilter, mock_classifier, mock_enricher
):
    mock_scraper_runner.scrape_data_from_sources.return_value = 1

    status = PipelineRunner.run([])

    assert status == 1
    mock_silver_ingest.return_value.run.assert_not_called()
    mock_silver_export.return_value.export.assert_not_called()
    mock_prefilter.main.assert_not_called()


@_patch_stage("JobEnricherMain")
@_patch_stage("JobClassifierMain")
@_patch_stage("JobPrefilterMain")
@_patch_stage("SilverExport")
@_patch_stage("SilverIngest")
@_patch_stage("ScraperRunner")
def test_stops_when_silver_export_is_empty(
    mock_scraper_runner, mock_silver_ingest, mock_silver_export, mock_prefilter, mock_classifier, mock_enricher
):
    mock_scraper_runner.scrape_data_from_sources.return_value = 0
    mock_silver_ingest.return_value.run.return_value = 0
    mock_silver_export.return_value.export.return_value = 0

    status = PipelineRunner.run([])

    assert status == 1
    mock_prefilter.main.assert_not_called()


@_patch_stage("JobEnricherMain")
@_patch_stage("JobClassifierMain")
@_patch_stage("JobPrefilterMain")
@_patch_stage("SilverExport")
@_patch_stage("SilverIngest")
@_patch_stage("ScraperRunner")
def test_skip_flags_bypass_scrape_and_silver_build(
    mock_scraper_runner, mock_silver_ingest, mock_silver_export, mock_prefilter, mock_classifier, mock_enricher
):
    mock_silver_export.return_value.export.return_value = 5
    mock_prefilter.main.return_value = 0
    mock_classifier.main.return_value = 0
    mock_enricher.main.return_value = 0

    status = PipelineRunner.run(["--skip-scrape", "--skip-silver-build"])

    assert status == 0
    mock_scraper_runner.scrape_data_from_sources.assert_not_called()
    mock_silver_ingest.return_value.run.assert_not_called()
    mock_silver_export.return_value.export.assert_called_once()


@_patch_stage("JobEnricherMain")
@_patch_stage("JobClassifierMain")
@_patch_stage("JobPrefilterMain")
@_patch_stage("SilverExport")
@_patch_stage("SilverIngest")
@_patch_stage("ScraperRunner")
def test_company_flag_is_passed_through_to_scrape_stage(
    mock_scraper_runner, mock_silver_ingest, mock_silver_export, mock_prefilter, mock_classifier, mock_enricher
):
    mock_scraper_runner.scrape_data_from_sources.return_value = 0
    mock_silver_ingest.return_value.run.return_value = 0
    mock_silver_export.return_value.export.return_value = 5
    mock_prefilter.main.return_value = 0
    mock_classifier.main.return_value = 0
    mock_enricher.main.return_value = 0

    PipelineRunner.run(["--company", "stack_av"])

    mock_scraper_runner.scrape_data_from_sources.assert_called_once_with(["--company", "stack_av"])


@_patch_stage("JobEnricherMain")
@_patch_stage("JobClassifierMain")
@_patch_stage("JobPrefilterMain")
@_patch_stage("SilverExport")
@_patch_stage("SilverIngest")
@_patch_stage("ScraperRunner")
def test_stops_when_silver_dbt_build_fails(
    mock_scraper_runner, mock_silver_ingest, mock_silver_export, mock_prefilter, mock_classifier, mock_enricher
):
    mock_scraper_runner.scrape_data_from_sources.return_value = 0
    mock_silver_ingest.return_value.run.return_value = 1

    status = PipelineRunner.run([])

    assert status == 1
    mock_silver_export.return_value.export.assert_not_called()
    mock_prefilter.main.assert_not_called()


@_patch_stage("JobEnricherMain")
@_patch_stage("JobClassifierMain")
@_patch_stage("JobPrefilterMain")
@_patch_stage("SilverExport")
@_patch_stage("SilverIngest")
@_patch_stage("ScraperRunner")
def test_stops_and_propagates_status_when_prefilter_fails(
    mock_scraper_runner, mock_silver_ingest, mock_silver_export, mock_prefilter, mock_classifier, mock_enricher
):
    mock_scraper_runner.scrape_data_from_sources.return_value = 0
    mock_silver_ingest.return_value.run.return_value = 0
    mock_silver_export.return_value.export.return_value = 5
    mock_prefilter.main.return_value = 1

    status = PipelineRunner.run([])

    assert status == 1
    mock_classifier.main.assert_not_called()
    mock_enricher.main.assert_not_called()


@_patch_stage("JobEnricherMain")
@_patch_stage("JobClassifierMain")
@_patch_stage("JobPrefilterMain")
@_patch_stage("SilverExport")
@_patch_stage("SilverIngest")
@_patch_stage("ScraperRunner")
def test_stops_and_propagates_status_when_relevance_classification_fails(
    mock_scraper_runner, mock_silver_ingest, mock_silver_export, mock_prefilter, mock_classifier, mock_enricher
):
    mock_scraper_runner.scrape_data_from_sources.return_value = 0
    mock_silver_ingest.return_value.run.return_value = 0
    mock_silver_export.return_value.export.return_value = 5
    mock_prefilter.main.return_value = 0
    mock_classifier.main.return_value = 1

    status = PipelineRunner.run([])

    assert status == 1
    mock_enricher.main.assert_not_called()


@_patch_stage("JobEnricherMain")
@_patch_stage("JobClassifierMain")
@_patch_stage("JobPrefilterMain")
@_patch_stage("SilverExport")
@_patch_stage("SilverIngest")
@_patch_stage("ScraperRunner")
def test_propagates_status_when_enrichment_fails(
    mock_scraper_runner, mock_silver_ingest, mock_silver_export, mock_prefilter, mock_classifier, mock_enricher
):
    mock_scraper_runner.scrape_data_from_sources.return_value = 0
    mock_silver_ingest.return_value.run.return_value = 0
    mock_silver_export.return_value.export.return_value = 5
    mock_prefilter.main.return_value = 0
    mock_classifier.main.return_value = 0
    mock_enricher.main.return_value = 1

    status = PipelineRunner.run([])

    assert status == 1


@_patch_stage("JobEnricherMain")
@_patch_stage("JobClassifierMain")
@_patch_stage("JobPrefilterMain")
@_patch_stage("SilverExport")
@_patch_stage("SilverIngest")
@_patch_stage("ScraperRunner")
def test_prefilter_config_flag_is_passed_through_to_prefilter_stage(
    mock_scraper_runner, mock_silver_ingest, mock_silver_export, mock_prefilter, mock_classifier, mock_enricher
):
    mock_scraper_runner.scrape_data_from_sources.return_value = 0
    mock_silver_ingest.return_value.run.return_value = 0
    mock_silver_export.return_value.export.return_value = 5
    mock_prefilter.main.return_value = 0
    mock_classifier.main.return_value = 0
    mock_enricher.main.return_value = 0

    PipelineRunner.run(["--prefilter-config", "custom_prefilter.yaml"])

    prefilter_argv = mock_prefilter.main.call_args.args[0]
    assert "--config" in prefilter_argv
    assert prefilter_argv[prefilter_argv.index("--config") + 1] == "custom_prefilter.yaml"
