from unittest.mock import patch
import importlib

from scrapers.utils.run_company import run_company
from scrapers.utils.runner import ScraperRunner
from scrapers.scraper_main import main

run_company_mod = importlib.import_module("scrapers.utils.run_company")


def test_run_company_skips_missing_slug():
    count = run_company(
        {"name": "Example", "ats": "greenhouse", "slug": None},
        max_jobs=10,
        timeout=5,
    )

    assert count == 0


@patch.object(run_company_mod, "APIStrategy")
def test_run_company_returns_fetched_count(mock_strategy):
    mock_strategy.return_value.fetch_postings.return_value = [{"id": "1"}, {"id": "2"}]
    company = {
        "name": "Stack AV",
        "ats": "greenhouse",
        "slug": "stackav",
    }

    count = run_company(company, max_jobs=10, timeout=5)

    assert count == 2
    mock_strategy.assert_called_once_with(
        ats_name="greenhouse",
        slug="stackav",
        company_name="Stack AV",
    )


@patch("scrapers.utils.runner.run_company")
@patch("scrapers.utils.runner.CompanyRegistry")
def test_runner_returns_error_when_company_key_missing(mock_registry, mock_run):
    mock_registry.load_company_list.return_value = []
    mock_registry.enabled_api_sources.return_value = []

    status = ScraperRunner.run(["--company", "does_not_exist"])

    assert status == 1
    mock_run.assert_not_called()


@patch("scrapers.utils.runner.run_company")
@patch("scrapers.utils.runner.CompanyRegistry")
def test_runner_continues_after_company_failure(mock_registry, mock_run):
    mock_registry.load_company_list.return_value = [{"key": "a"}, {"key": "b"}]
    mock_registry.enabled_api_sources.return_value = [
        {"key": "a", "name": "A", "ats": "greenhouse", "slug": "a"},
        {"key": "b", "name": "B", "ats": "greenhouse", "slug": "b"},
    ]
    mock_run.side_effect = [RuntimeError("HTTP 403"), 4]

    status = ScraperRunner.run(["--max-jobs", "10"])

    assert status == 1
    assert mock_run.call_count == 2


@patch("scrapers.utils.runner.ScraperRunner.run", return_value=0)
def test_scraper_main_delegates_to_runner(mock_run):
    assert main(["--company", "stack_av"]) == 0
    mock_run.assert_called_once_with(["--company", "stack_av"])
