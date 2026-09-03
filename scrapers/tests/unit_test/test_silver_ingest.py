from unittest.mock import MagicMock

from scrapers.service.silver_cleaning.silver_ingest import SilverIngest


def test_ingest_builds_silver_through_dbt():
    postgres_config = MagicMock()
    dbt_config = MagicMock()
    dbt_config.run.return_value = 0

    assert SilverIngest(postgres_config, dbt_config).run() == 0

    dbt_config.run.assert_called_once_with("+cleaned_job_postings", postgres_config)
