from unittest.mock import MagicMock, patch

from scrapers.service.silver_cleaning.silver_ingest import SilverIngest, main


def test_ingest_builds_silver_through_dbt():
    postgres_config = MagicMock()
    dbt_config = MagicMock()
    dbt_config.run.return_value = 0

    assert SilverIngest(postgres_config, dbt_config).run() == 0

    dbt_config.run.assert_called_once_with("+cleaned_job_postings", postgres_config)


@patch("scrapers.service.silver_cleaning.silver_ingest.SilverIngest")
def test_main_returns_silver_ingest_run_status(mock_silver_ingest):
    mock_silver_ingest.return_value.run.return_value = 1

    assert main() == 1

    mock_silver_ingest.return_value.run.assert_called_once()
