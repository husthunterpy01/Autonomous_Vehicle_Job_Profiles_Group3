import json
from unittest.mock import MagicMock, patch

from psycopg2.extras import Json

from scrapers.scraper_main import main
from scrapers.utils.company_scraper import CompanyScraper


def _urlopen_json(payload):
    body = json.dumps(payload).encode("utf-8")
    mock_response = MagicMock()
    mock_response.read.return_value = body
    mock_response.status = 200
    mock_response.getcode.return_value = 200
    mock_response.headers = {"Content-Type": "application/json"}
    mock_response.__enter__.return_value = mock_response
    mock_response.__exit__.return_value = False
    return mock_response


def _stub_postgres(mock_connect):
    connection = mock_connect.return_value
    connection.cursor.return_value.__enter__.return_value = MagicMock()
    return connection


def _archive_minio_client(mock_minio, stored):
    stored.setdefault("objects", {})

    def put_object(**kwargs):
        payload = kwargs["data"].read()
        stored["object_name"] = kwargs["object_name"]
        stored["bucket"] = kwargs["bucket_name"]
        stored["bytes"] = payload
        stored["objects"][kwargs["object_name"]] = payload

    def list_objects(**_kwargs):
        objects = []
        for name in stored["objects"]:
            obj = MagicMock()
            obj.object_name = name
            objects.append(obj)
        return objects

    def get_object(_bucket, object_name):
        response = MagicMock()
        response.read.return_value = stored["objects"][object_name]
        return response

    client = mock_minio.return_value
    client.bucket_exists.return_value = False
    client.put_object.side_effect = put_object
    client.list_objects.side_effect = list_objects
    client.get_object.side_effect = get_object
    return client


def test_registry_loads_checked_in_company_list():
    companies = CompanyScraper.load_company_list()
    keys = {row["key"] for row in companies}

    assert "stack_av" in keys
    assert "waabi" in keys
    waabi = next(row for row in companies if row["key"] == "waabi")
    assert waabi["ats"] == "lever"
    assert waabi["slug"] == "waabi"


def test_enabled_api_sources_uses_enabled_flag_from_real_yaml():
    companies = CompanyScraper.load_company_list()
    selected = CompanyScraper.enabled_api_sources(companies)
    selected_keys = {row["key"] for row in selected}
    enabled_api = {
        row["key"]
        for row in companies
        if row.get("enabled") and row.get("ats") in CompanyScraper.API_ATS
    }

    assert "stack_av" in selected_keys
    assert selected_keys == enabled_api
    disabled = [row["key"] for row in companies if not row.get("enabled")]
    assert not any(key in selected_keys for key in disabled)


@patch("scrapers.service.bronze_storage.bronze_ingest.shutil.which", return_value="/usr/bin/dbt")
@patch("scrapers.service.bronze_storage.bronze_ingest.subprocess.run")
@patch("scrapers.service.bronze_storage.bronze_ingest.execute_values")
@patch("scrapers.service.bronze_storage.bronze_ingest.psycopg2.connect")
@patch("scrapers.response_archive.Minio")
@patch("scrapers.service.fetch.rawfetch.urlopen")
def test_stack_av_scrape_lands_raw_and_runs_dbt(
    mock_urlopen, mock_minio, mock_connect, mock_execute_values, mock_dbt, _mock_which
):
    stored = {}
    greenhouse_payload = {
        "jobs": [
            {
                "id": "101",
                "title": "Software Engineer",
                "content": "<p>Build autonomy software</p>",
                "location": {"name": "Pittsburgh, PA"},
                "first_published": "2026-08-01T00:00:00Z",
                "absolute_url": "https://job-boards.greenhouse.io/stackav/jobs/101",
            },
            {
                "id": "102",
                "title": "ML Engineer",
                "content": "<p>Train models</p>",
                "location": {"name": "Remote"},
                "first_published": "2026-08-02T00:00:00Z",
                "absolute_url": "https://job-boards.greenhouse.io/stackav/jobs/102",
            },
        ],
        "meta": {"total": 2},
    }
    mock_urlopen.return_value = _urlopen_json(greenhouse_payload)
    client = _archive_minio_client(mock_minio, stored)
    _stub_postgres(mock_connect)
    mock_dbt.return_value = MagicMock(returncode=0)

    status = main(["--company", "stack_av", "--max-jobs", "1"])

    assert status == 0
    request = mock_urlopen.call_args[0][0]
    assert request.get_header("User-agent") == "Mozilla/5.0"
    assert request.full_url.endswith("/boards/stackav/jobs?content=true")
    assert stored["object_name"].startswith("api/stack_av/")
    assert stored["object_name"].endswith(".parquet")
    client.make_bucket.assert_called_once()

    inserted = mock_execute_values.call_args.args[2][0]
    assert inserted[0] == "Stack AV"
    assert inserted[1] == "stack_av"
    assert inserted[2] == "api"
    assert inserted[3] == "greenhouse"
    assert isinstance(inserted[4], Json)
    assert inserted[4].adapted == greenhouse_payload
    assert inserted[5] == "US"
    assert "raw_responses" in mock_execute_values.call_args.args[1]

    dbt_cmd = mock_dbt.call_args.args[0]
    assert dbt_cmd[0] == "/usr/bin/dbt"
    assert "run" in dbt_cmd
    assert "job_postings" in dbt_cmd
    assert "./scrapers/dbt" in dbt_cmd


@patch("scrapers.service.bronze_storage.bronze_ingest.shutil.which", return_value="/usr/bin/dbt")
@patch("scrapers.service.bronze_storage.bronze_ingest.subprocess.run")
@patch("scrapers.service.bronze_storage.bronze_ingest.execute_values")
@patch("scrapers.service.bronze_storage.bronze_ingest.psycopg2.connect")
@patch("scrapers.response_archive.Minio")
@patch("scrapers.service.fetch.rawfetch.urlopen")
def test_ashby_http_403_still_runs_dbt_bronze(
    mock_urlopen, mock_minio, mock_connect, mock_execute_values, mock_dbt, _mock_which
):
    from urllib.error import HTTPError

    mock_urlopen.side_effect = HTTPError(
        url="https://api.ashbyhq.com/posting-api/job-board/42dot",
        code=403,
        msg="Forbidden",
        hdrs=None,
        fp=None,
    )
    _archive_minio_client(mock_minio, {})
    _stub_postgres(mock_connect)
    mock_dbt.return_value = MagicMock(returncode=0)

    status = main(["--company", "fortytwo_dot", "--max-jobs", "1"])

    assert status == 1
    mock_minio.return_value.put_object.assert_not_called()
    mock_execute_values.assert_not_called()
    mock_dbt.assert_called_once()
    assert "job_postings" in mock_dbt.call_args.args[0]


@patch("scrapers.service.bronze_storage.bronze_ingest.shutil.which", return_value="/usr/bin/dbt")
@patch("scrapers.service.bronze_storage.bronze_ingest.subprocess.run")
@patch("scrapers.service.bronze_storage.bronze_ingest.execute_values")
@patch("scrapers.service.bronze_storage.bronze_ingest.psycopg2.connect")
@patch("scrapers.response_archive.Minio")
@patch("scrapers.service.fetch.rawfetch.urlopen")
def test_pipeline_fails_when_dbt_bronze_run_fails(
    mock_urlopen, mock_minio, mock_connect, mock_execute_values, mock_dbt, _mock_which
):
    stored = {}
    mock_urlopen.return_value = _urlopen_json(
        {"jobs": [{"id": "101", "title": "Software Engineer"}], "meta": {"total": 1}}
    )
    _archive_minio_client(mock_minio, stored)
    _stub_postgres(mock_connect)
    mock_dbt.return_value = MagicMock(returncode=1)

    status = main(["--company", "stack_av"])

    assert status == 1
    mock_execute_values.assert_called()
    mock_dbt.assert_called_once()


@patch("scrapers.service.bronze_storage.bronze_ingest.shutil.which", return_value="/usr/bin/dbt")
@patch("scrapers.service.bronze_storage.bronze_ingest.subprocess.run")
@patch("scrapers.service.bronze_storage.bronze_ingest.execute_values")
@patch("scrapers.service.bronze_storage.bronze_ingest.psycopg2.connect")
@patch("scrapers.response_archive.Minio")
@patch("scrapers.service.fetch.rawfetch.urlopen")
def test_waabi_lever_scrape_lands_array_payload(
    mock_urlopen, mock_minio, mock_connect, mock_execute_values, mock_dbt, _mock_which
):
    stored = {}
    lever_payload = [
        {
            "text": "Software Engineer",
            "descriptionPlain": "Build the driver.",
            "categories": {"location": "Toronto, ON"},
            "hostedUrl": "https://jobs.lever.co/waabi/abc",
            "createdAt": 1690000000000,
            "workplaceType": "hybrid",
        }
    ]
    mock_urlopen.return_value = _urlopen_json(lever_payload)
    _archive_minio_client(mock_minio, stored)
    _stub_postgres(mock_connect)
    mock_dbt.return_value = MagicMock(returncode=0)

    status = main(["--company", "waabi"])

    assert status == 0
    request = mock_urlopen.call_args[0][0]
    assert request.full_url == "https://api.lever.co/v0/postings/waabi"
    assert stored["object_name"].startswith("api/waabi/")
    inserted = mock_execute_values.call_args.args[2][0]
    assert inserted[0] == "Waabi"
    assert inserted[3] == "lever"
    assert inserted[4].adapted == lever_payload
    assert inserted[5] == "CA"


@patch("scrapers.service.bronze_storage.bronze_ingest.shutil.which", return_value="/usr/bin/dbt")
@patch("scrapers.service.bronze_storage.bronze_ingest.subprocess.run")
@patch("scrapers.service.bronze_storage.bronze_ingest.execute_values")
@patch("scrapers.service.bronze_storage.bronze_ingest.psycopg2.connect")
@patch("scrapers.response_archive.Minio")
@patch("scrapers.service.fetch.rawfetch.urlopen")
def test_ashby_scrape_lands_multi_location_payload(
    mock_urlopen, mock_minio, mock_connect, mock_execute_values, mock_dbt, _mock_which
):
    stored = {}
    ashby_payload = {
        "jobs": [
            {
                "title": "Autonomy Engineer",
                "descriptionPlain": "Ship autonomy software.",
                "location": "Seoul",
                "secondaryLocations": [{"location": "Mountain View"}],
                "jobUrl": "https://jobs.ashbyhq.com/42dot/job-1",
                "publishedAt": "2026-08-01T00:00:00Z",
                "employmentType": "FullTime",
            }
        ]
    }
    mock_urlopen.return_value = _urlopen_json(ashby_payload)
    _archive_minio_client(mock_minio, stored)
    _stub_postgres(mock_connect)
    mock_dbt.return_value = MagicMock(returncode=0)

    status = main(["--company", "fortytwo_dot"])

    assert status == 0
    request = mock_urlopen.call_args[0][0]
    assert request.full_url.endswith("/posting-api/job-board/42dot")
    assert stored["object_name"].startswith("api/42dot/")
    inserted = mock_execute_values.call_args.args[2][0]
    assert inserted[0] == "42dot"
    assert inserted[3] == "ashby"
    assert inserted[4].adapted == ashby_payload
    assert inserted[5] == "KR"


@patch("scrapers.service.bronze_storage.bronze_ingest.shutil.which", return_value="/usr/bin/dbt")
@patch("scrapers.service.bronze_storage.bronze_ingest.subprocess.run")
@patch("scrapers.service.bronze_storage.bronze_ingest.execute_values")
@patch("scrapers.service.bronze_storage.bronze_ingest.psycopg2.connect")
@patch("scrapers.response_archive.Minio")
@patch("scrapers.service.fetch.rawfetch.urlopen")
def test_bosch_smartrecruiters_scrape_lands_content_payload(
    mock_urlopen, mock_minio, mock_connect, mock_execute_values, mock_dbt, _mock_which
):
    stored = {}
    list_payload = {
        "content": [
            {
                "id": "744000146470121",
                "name": "Product Data Operator - Temporary",
                "location": {"fullLocation": "Beograd, , Serbia"},
            }
        ]
    }
    detail_payload = {
        "id": "744000146470121",
        "name": "Product Data Operator - Temporary",
        "postingUrl": "https://jobs.smartrecruiters.com/BoschGroup/744000146470121-product-data-operator-temporary",
        "location": {"fullLocation": "Beograd, , Serbia"},
        "releasedDate": "2026-08-31T13:38:57.052Z",
        "typeOfEmployment": {"id": "permanent", "label": "Full-time"},
        "jobAd": {
            "sections": {
                "jobDescription": {
                    "title": "Job Description",
                    "text": "<p>Release product documents</p>",
                }
            }
        },
    }
    mock_urlopen.side_effect = [
        _urlopen_json(list_payload),
        _urlopen_json(detail_payload),
    ]
    _archive_minio_client(mock_minio, stored)
    _stub_postgres(mock_connect)
    mock_dbt.return_value = MagicMock(returncode=0)

    with patch("scrapers.service.fetch.rawfetch.time.sleep"):
        status = main(["--company", "bosch"])

    assert status == 0
    urls = [call.args[0].full_url for call in mock_urlopen.call_args_list]
    assert urls[0] == "https://api.smartrecruiters.com/v1/companies/BoschGroup/postings"
    assert urls[1].endswith("/postings/744000146470121")
    assert stored["object_name"].startswith("api/bosch/")
    inserted = mock_execute_values.call_args.args[2][0]
    assert inserted[0] == "Bosch"
    assert inserted[3] == "smartrecruiters"
    assert inserted[4].adapted["content"][0]["jobAd"]["sections"]["jobDescription"]["text"] == (
        "<p>Release product documents</p>"
    )
    assert inserted[5] == "DE"


@patch("scrapers.response_archive.Minio")
@patch("scrapers.service.fetch.rawfetch.urlopen")
def test_unknown_company_does_not_scrape_or_ingest(mock_urlopen, mock_minio):
    status = main(["--company", "does_not_exist"])

    assert status == 1
    mock_urlopen.assert_not_called()
    mock_minio.assert_not_called()


@patch("scrapers.service.bronze_storage.bronze_ingest.shutil.which", return_value="/usr/bin/dbt")
@patch("scrapers.service.bronze_storage.bronze_ingest.subprocess.run")
@patch("scrapers.service.bronze_storage.bronze_ingest.execute_values")
@patch("scrapers.service.bronze_storage.bronze_ingest.psycopg2.connect")
@patch("scrapers.response_archive.Minio")
@patch("scrapers.service.fetch.rawfetch.urlopen")
def test_postgres_connect_failure_after_scrape_returns_error(
    mock_urlopen, mock_minio, mock_connect, mock_execute_values, mock_dbt, _mock_which
):
    import psycopg2

    stored = {}
    mock_urlopen.return_value = _urlopen_json(
        {"jobs": [{"id": "101", "title": "Engineer"}], "meta": {"total": 1}}
    )
    _archive_minio_client(mock_minio, stored)
    mock_connect.side_effect = psycopg2.OperationalError("could not connect")
    mock_dbt.return_value = MagicMock(returncode=0)

    status = main(["--company", "stack_av"])

    assert status == 1
    assert stored["object_name"].startswith("api/stack_av/")
    mock_execute_values.assert_not_called()
    mock_dbt.assert_not_called()


@patch("scrapers.service.bronze_storage.bronze_ingest.shutil.which", return_value="/usr/bin/dbt")
@patch("scrapers.service.bronze_storage.bronze_ingest.subprocess.run")
@patch("scrapers.service.bronze_storage.bronze_ingest.execute_values")
@patch("scrapers.service.bronze_storage.bronze_ingest.psycopg2.connect")
@patch("scrapers.response_archive.Minio")
def test_ingest_lands_latest_parquet_per_company(
    mock_minio, mock_connect, mock_execute_values, mock_dbt, _mock_which
):
    from datetime import datetime, timezone

    from scrapers.response_archive import ResponseArchive
    from scrapers.service.bronze_storage.bronze_ingest import BronzeIngest

    def _parquet(body, fetched_at):
        return ResponseArchive._to_parquet_bytes(
            [
                {
                    "source": "api",
                    "company": "Stack AV",
                    "source_system": "greenhouse",
                    "url": "",
                    "status": 200,
                    "content_type": "application/json",
                    "body": json.dumps(body),
                    "fetched_at": fetched_at,
                }
            ]
        )

    older = {"jobs": [{"title": "Old Role"}]}
    newer = {"jobs": [{"title": "New Role"}]}
    stored = {
        "objects": {
            "api/stack_av/stack_av_2026-08-30_01-00-00.parquet": _parquet(
                older, datetime(2026, 8, 30, tzinfo=timezone.utc)
            ),
            "api/stack_av/stack_av_2026-08-31_12-00-00.parquet": _parquet(
                newer, datetime(2026, 8, 31, 12, tzinfo=timezone.utc)
            ),
        }
    }
    _archive_minio_client(mock_minio, stored)
    _stub_postgres(mock_connect)
    mock_dbt.return_value = MagicMock(returncode=0)

    status = BronzeIngest("av-scraped-jobs").extract_raw_data_to_db()

    assert status == 0
    inserted = mock_execute_values.call_args.args[2][0]
    assert inserted[4].adapted == newer
    mock_dbt.assert_called_once()


@patch("scrapers.service.bronze_storage.bronze_ingest.shutil.which", return_value="/usr/bin/dbt")
@patch("scrapers.service.bronze_storage.bronze_ingest.subprocess.run")
@patch("scrapers.service.bronze_storage.bronze_ingest.execute_values")
@patch("scrapers.service.bronze_storage.bronze_ingest.psycopg2.connect")
@patch("scrapers.response_archive.Minio")
def test_html_archive_is_skipped_before_dbt(
    mock_minio, mock_connect, mock_execute_values, mock_dbt, _mock_which
):
    from datetime import datetime, timezone

    from scrapers.response_archive import ResponseArchive
    from scrapers.service.bronze_storage.bronze_ingest import BronzeIngest

    stored = {
        "objects": {
            "html/waymo/waymo_2026-08-31_12-00-00.parquet": ResponseArchive._to_parquet_bytes(
                [
                    {
                        "source": "html",
                        "company": "Waymo",
                        "source_system": "html",
                        "url": "https://careers.withwaymo.com/",
                        "status": 200,
                        "content_type": "text/html",
                        "body": "<html></html>",
                        "fetched_at": datetime(2026, 8, 31, tzinfo=timezone.utc),
                    }
                ]
            )
        }
    }
    _archive_minio_client(mock_minio, stored)
    _stub_postgres(mock_connect)
    mock_dbt.return_value = MagicMock(returncode=0)

    status = BronzeIngest("av-scraped-jobs").extract_raw_data_to_db()

    assert status == 0
    mock_execute_values.assert_not_called()
    mock_dbt.assert_called_once()
