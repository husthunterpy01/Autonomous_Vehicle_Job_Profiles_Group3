from unittest.mock import patch

from scrapers.utils.company_scraper import CompanyScraper
from scrapers.utils.runner import ScraperRunner
from scrapers.scraper_main import main


def test_scrape_company_skips_missing_slug():
    count = CompanyScraper.scrape_company(
        {"name": "Example", "ats": "greenhouse", "slug": None},
        timeout=5,
    )

    assert count == 0


@patch("scrapers.utils.company_scraper.RawFetch")
def test_scrape_company_archives_one_payload(mock_fetch):
    mock_fetch.from_company.return_value = (mock_fetch.return_value, "https://example/jobs")
    mock_fetch.return_value.fetch_and_archive.return_value = "api/stack_av/file.parquet"
    company = {
        "name": "Stack AV",
        "ats": "greenhouse",
        "slug": "stackav",
    }

    count = CompanyScraper.scrape_company(company, timeout=5)

    assert count == 1
    mock_fetch.from_company.assert_called_once_with(company)
    mock_fetch.return_value.fetch_and_archive.assert_called_once_with(
        "https://example/jobs", timeout=5
    )


@patch("scrapers.utils.runner.ScraperRunner.upload_to_bronze_table")
@patch("scrapers.utils.runner.CompanyScraper")
def test_runner_returns_error_when_company_key_missing(mock_scraper, mock_upload):
    mock_scraper.load_company_list.return_value = []
    mock_scraper.enabled_api_sources.return_value = []

    status = ScraperRunner.scrape_data_from_sources(["--company", "does_not_exist"])

    assert status == 1
    mock_scraper.scrape_company.assert_not_called()
    mock_upload.assert_not_called()


@patch("scrapers.utils.runner.ScraperRunner.upload_to_bronze_table", return_value=0)
@patch("scrapers.utils.runner.CompanyScraper")
def test_runner_continues_after_company_failure(mock_scraper, mock_upload):
    mock_scraper.load_company_list.return_value = [{"key": "a"}, {"key": "b"}]
    mock_scraper.enabled_api_sources.return_value = [
        {"key": "a", "name": "A", "ats": "greenhouse", "slug": "a"},
        {"key": "b", "name": "B", "ats": "greenhouse", "slug": "b"},
    ]
    mock_scraper.scrape_company.side_effect = [RuntimeError("HTTP 403"), 4]

    status = ScraperRunner.scrape_data_from_sources(["--max-jobs", "10"])

    assert status == 1
    assert mock_scraper.scrape_company.call_count == 2
    mock_upload.assert_called_once_with()


@patch("scrapers.utils.runner.ScraperRunner.upload_to_bronze_table", return_value=0)
@patch("scrapers.utils.runner.CompanyScraper")
def test_runner_uploads_to_bronze_after_scrape(mock_scraper, mock_upload):
    mock_scraper.load_company_list.return_value = [{"key": "stack_av"}]
    mock_scraper.enabled_api_sources.return_value = [
        {"key": "stack_av", "name": "Stack AV", "ats": "greenhouse", "slug": "stackav"}
    ]
    mock_scraper.scrape_company.return_value = 1

    status = ScraperRunner.scrape_data_from_sources(["--company", "stack_av"])

    assert status == 0
    mock_scraper.scrape_company.assert_called_once()
    mock_upload.assert_called_once_with()


@patch("scrapers.utils.runner.ScraperRunner.upload_to_bronze_table", return_value=1)
@patch("scrapers.utils.runner.CompanyScraper")
def test_runner_returns_error_when_bronze_upload_fails(mock_scraper, mock_upload):
    mock_scraper.load_company_list.return_value = [{"key": "stack_av"}]
    mock_scraper.enabled_api_sources.return_value = [
        {"key": "stack_av", "name": "Stack AV", "ats": "greenhouse", "slug": "stackav"}
    ]
    mock_scraper.scrape_company.return_value = 1

    status = ScraperRunner.scrape_data_from_sources(["--company", "stack_av"])

    assert status == 1
    mock_upload.assert_called_once_with()


@patch("scrapers.utils.runner.ScraperRunner.scrape_data_from_sources", return_value=0)
def test_scraper_main_delegates_to_runner(mock_run):
    assert main(["--company", "stack_av"]) == 0
    mock_run.assert_called_once_with(["--company", "stack_av"])
