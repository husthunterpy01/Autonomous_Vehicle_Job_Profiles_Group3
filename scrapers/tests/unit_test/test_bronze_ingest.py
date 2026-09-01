import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
from psycopg2.extras import Json

from scrapers.service.bronze_storage.bronze_ingest import BronzeIngest

DBT_JOB_POSTINGS = (
    Path(__file__).resolve().parents[2] / "dbt" / "models" / "bronze" / "job_postings.sql"
)


def _archive_frame(body, source_system="greenhouse", company="Stack AV"):
    if not isinstance(body, str):
        body = json.dumps(body)
    return pd.DataFrame(
        [
            {
                "source": "api",
                "company": company,
                "source_system": source_system,
                "body": body,
            }
        ]
    )


@patch("scrapers.config.dbt.shutil.which", return_value="/usr/bin/dbt")
@patch("scrapers.config.dbt.subprocess.run")
@patch("scrapers.service.bronze_storage.bronze_ingest.psycopg2.connect")
@patch("scrapers.service.bronze_storage.bronze_ingest.ResponseArchive")
@patch("scrapers.service.bronze_storage.bronze_ingest.CompanyScraper")
@patch("scrapers.service.bronze_storage.bronze_ingest.execute_values")
def test_extract_lands_raw_payload_then_runs_dbt(
    mock_execute_values, mock_companies, mock_archive, mock_connect, mock_dbt, _mock_which
):
    mock_companies.load_company_list.return_value = [
        {"key": "stack_av", "name": "Stack AV", "country": "US"}
    ]
    mock_archive.return_value._extract_data_from_storage.return_value = [
        ("api", "stack_av", _archive_frame({"jobs": [{"title": "Engineer"}]}))
    ]
    mock_dbt.return_value = MagicMock(returncode=0)
    connection = mock_connect.return_value
    cursor = MagicMock()
    connection.cursor.return_value.__enter__.return_value = cursor

    status = BronzeIngest("av-scraped-jobs").extract_raw_data_to_db()

    assert status == 0
    inserted = mock_execute_values.call_args.args[2][0]
    assert inserted[0] == "Stack AV"
    assert inserted[1] == "stack_av"
    assert inserted[2] == "api"
    assert inserted[3] == "greenhouse"
    assert isinstance(inserted[4], Json)
    assert inserted[4].adapted == {"jobs": [{"title": "Engineer"}]}
    assert inserted[5] == "US"
    assert "./scrapers/dbt" in mock_dbt.call_args.args[0]
    assert "job_postings" in mock_dbt.call_args.args[0]
    connection.close.assert_called_once()


@patch("scrapers.config.dbt.shutil.which", return_value="/usr/bin/dbt")
@patch("scrapers.config.dbt.subprocess.run")
@patch("scrapers.service.bronze_storage.bronze_ingest.psycopg2.connect")
@patch("scrapers.service.bronze_storage.bronze_ingest.ResponseArchive")
@patch("scrapers.service.bronze_storage.bronze_ingest.CompanyScraper")
@patch("scrapers.service.bronze_storage.bronze_ingest.execute_values")
def test_extract_skips_html_source(
    mock_execute_values, mock_companies, mock_archive, mock_connect, mock_dbt, _mock_which
):
    mock_archive.return_value._extract_data_from_storage.return_value = [
        ("html", "waymo", _archive_frame("<html></html>", source_system="html", company="Waymo"))
    ]
    mock_dbt.return_value = MagicMock(returncode=0)
    connection = mock_connect.return_value
    connection.cursor.return_value.__enter__.return_value = MagicMock()

    status = BronzeIngest("av-scraped-jobs").extract_raw_data_to_db()

    assert status == 0
    mock_execute_values.assert_not_called()
    mock_dbt.assert_called_once()


@patch("scrapers.config.dbt.shutil.which", return_value="/usr/bin/dbt")
@patch("scrapers.config.dbt.subprocess.run")
@patch("scrapers.service.bronze_storage.bronze_ingest.psycopg2.connect")
@patch("scrapers.service.bronze_storage.bronze_ingest.ResponseArchive")
@patch("scrapers.service.bronze_storage.bronze_ingest.CompanyScraper")
@patch("scrapers.service.bronze_storage.bronze_ingest.execute_values")
def test_extract_continues_after_company_failure(
    mock_execute_values, mock_companies, mock_archive, mock_connect, mock_dbt, _mock_which
):
    mock_companies.load_company_list.return_value = [
        {"key": "stack_av", "name": "Stack AV", "country": "US"},
        {"key": "waabi", "name": "Waabi", "country": "CA"},
    ]
    mock_archive.return_value._extract_data_from_storage.return_value = [
        ("api", "stack_av", _archive_frame("not-json")),
        ("api", "waabi", _archive_frame([{"text": "Engineer"}], source_system="lever", company="Waabi")),
    ]
    mock_dbt.return_value = MagicMock(returncode=0)
    connection = mock_connect.return_value
    connection.cursor.return_value.__enter__.return_value = MagicMock()

    status = BronzeIngest("av-scraped-jobs").extract_raw_data_to_db()

    assert status == 0
    assert mock_execute_values.call_count == 1
    inserted = mock_execute_values.call_args.args[2][0]
    assert inserted[0] == "Waabi"
    connection.rollback.assert_called()
    mock_dbt.assert_called_once()


@patch("scrapers.config.dbt.shutil.which", return_value="/usr/bin/dbt")
@patch("scrapers.config.dbt.subprocess.run")
@patch("scrapers.service.bronze_storage.bronze_ingest.psycopg2.connect")
@patch("scrapers.service.bronze_storage.bronze_ingest.ResponseArchive")
@patch("scrapers.service.bronze_storage.bronze_ingest.CompanyScraper")
def test_extract_returns_error_when_dbt_fails(
    mock_companies, mock_archive, mock_connect, mock_dbt, _mock_which
):
    mock_archive.return_value._extract_data_from_storage.return_value = []
    mock_dbt.return_value = MagicMock(returncode=1)
    mock_connect.return_value.cursor.return_value.__enter__.return_value = MagicMock()

    status = BronzeIngest("av-scraped-jobs").extract_raw_data_to_db()

    assert status == 1


def test_dbt_job_postings_model_covers_supported_ats():
    sql = DBT_JOB_POSTINGS.read_text(encoding="utf-8")
    for ats in ("greenhouse", "lever", "ashby", "smartrecruiters"):
        assert ats in sql
    assert "as id" in sql
    assert "row_number()" in sql
    assert "categories" in sql
    assert "commitment" in sql
    assert "workplaceType" not in sql


@patch("scrapers.config.dbt.shutil.which", return_value="/usr/bin/dbt")
@patch("scrapers.config.dbt.subprocess.run")
def test_dbt_config_run_uses_shared_project_dir(mock_dbt, _mock_which):
    from scrapers.config.dbt import DbtConfig
    from scrapers.config.postgres import PostgresConfig

    mock_dbt.return_value = MagicMock(returncode=0)
    postgres = PostgresConfig(host="db.local", port=5432, database="jobs", user="team3", password="secret")

    status = DbtConfig().run("job_postings", postgres)

    assert status == 0
    command = mock_dbt.call_args.args[0]
    assert command[:3] == ["/usr/bin/dbt", "run", "--project-dir"]
    assert command[3] == "./scrapers/dbt"
    assert command[5] == "./scrapers/dbt"
    assert "job_postings" in command
    assert mock_dbt.call_args.kwargs["env"]["POSTGRES_HOST"] == "db.local"
    assert mock_dbt.call_args.kwargs["env"]["POSTGRES_DB"] == "jobs"
