from unittest.mock import patch

from scrapers.utils.__main__ import ScraperMain


@patch("scrapers.utils.__main__.ScraperRunner")
def test_main_delegates_to_scraper_runner(mock_scraper_runner):
    """Regression test: ScraperMain.main used to call the nonexistent
    ScraperRunner.run, which would AttributeError the instant `python -m
    scrapers.utils` actually ran - nothing exercised this module before."""
    mock_scraper_runner.scrape_data_from_sources.return_value = 0

    status = ScraperMain.main(["--company", "stack_av"])

    assert status == 0
    mock_scraper_runner.scrape_data_from_sources.assert_called_once_with(["--company", "stack_av"])
