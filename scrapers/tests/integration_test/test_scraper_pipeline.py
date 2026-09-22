import json
import os
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


@patch("scrapers.config.dbt.shutil.which", return_value="/usr/bin/dbt")
@patch("scrapers.config.dbt.subprocess.run")
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
    # Greenhouse now makes one list call plus a per-job `pay_transparency=true`
    # detail call for each posting (see _expand_greenhouse_postings), so the
    # list request is the first call, not the last.
    request = mock_urlopen.call_args_list[0][0][0]
    assert request.get_header("User-agent").startswith("Mozilla/5.0")
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
    # The pay_transparency detail call (mocked with the same list payload,
    # which has no pay_input_ranges) attaches an empty array to each posting.
    expected_archived_payload = json.loads(json.dumps(greenhouse_payload))
    for job in expected_archived_payload["jobs"]:
        job["pay_input_ranges"] = []
    assert inserted[4].adapted == expected_archived_payload
    assert inserted[5] == "US"
    assert "raw_responses" in mock_execute_values.call_args.args[1]

    dbt_cmd = mock_dbt.call_args.args[0]
    assert dbt_cmd[0] == "/usr/bin/dbt"
    assert "run" in dbt_cmd
    assert "+job_postings" in dbt_cmd
    assert "./scrapers/dbt" in dbt_cmd


@patch("scrapers.config.dbt.shutil.which", return_value="/usr/bin/dbt")
@patch("scrapers.config.dbt.subprocess.run")
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
    assert "+job_postings" in mock_dbt.call_args.args[0]


@patch("scrapers.config.dbt.shutil.which", return_value="/usr/bin/dbt")
@patch("scrapers.config.dbt.subprocess.run")
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


@patch("scrapers.config.dbt.shutil.which", return_value="/usr/bin/dbt")
@patch("scrapers.config.dbt.subprocess.run")
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
            "categories": {"location": "Toronto, ON", "commitment": "Full-time"},
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


@patch("scrapers.config.dbt.shutil.which", return_value="/usr/bin/dbt")
@patch("scrapers.config.dbt.subprocess.run")
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


@patch("scrapers.config.dbt.shutil.which", return_value="/usr/bin/dbt")
@patch("scrapers.config.dbt.subprocess.run")
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


@patch("scrapers.config.dbt.shutil.which", return_value="/usr/bin/dbt")
@patch("scrapers.config.dbt.subprocess.run")
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


@patch("scrapers.config.dbt.shutil.which", return_value="/usr/bin/dbt")
@patch("scrapers.config.dbt.subprocess.run")
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


@patch("scrapers.config.dbt.shutil.which", return_value="/usr/bin/dbt")
@patch("scrapers.config.dbt.subprocess.run")
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


@patch("scrapers.service.fetch.rawfetch.time.sleep")
@patch("scrapers.config.dbt.shutil.which", return_value="/usr/bin/dbt")
@patch("scrapers.config.dbt.subprocess.run")
@patch("scrapers.service.bronze_storage.bronze_ingest.execute_values")
@patch("scrapers.service.bronze_storage.bronze_ingest.psycopg2.connect")
@patch("scrapers.response_archive.Minio")
@patch("scrapers.service.fetch.rawfetch.urlopen")
def test_gm_workday_scrape_paginates_and_attaches_job_details(
    mock_urlopen, mock_minio, mock_connect, mock_execute_values, mock_dbt, _mock_which, _mock_sleep
):
    """Workday is the only ATS with a paginated list POST plus a per-job
    detail GET carrying its own bot-defence headers (Referer/X-Requested-With)
    - none of the other per-ATS tests in this file exercise that path."""
    stored = {}
    list_payload = {
        "total": 1,
        "jobPostings": [
            {
                "title": "Staff Software Engineer",
                "externalPath": "/job/Detroit-MI/Staff-Software-Engineer_R12345",
                "bulletFields": ["R12345"],
            }
        ],
    }
    detail_payload = {
        "jobPostingInfo": {
            "title": "Staff Software Engineer",
            "jobDescription": "<p>Build autonomy software at GM.</p>",
            "location": "Detroit, MI",
        }
    }
    mock_urlopen.side_effect = [_urlopen_json(list_payload), _urlopen_json(detail_payload)]
    _archive_minio_client(mock_minio, stored)
    _stub_postgres(mock_connect)
    mock_dbt.return_value = MagicMock(returncode=0)

    status = main(["--company", "gm"])

    assert status == 0
    list_request = mock_urlopen.call_args_list[0][0][0]
    assert list_request.get_method() == "POST"
    assert list_request.full_url == "https://generalmotors.wd5.myworkdayjobs.com/wday/cxs/generalmotors/Careers_GM/jobs"
    assert json.loads(list_request.data)["offset"] == 0

    detail_request = mock_urlopen.call_args_list[1][0][0]
    assert detail_request.full_url == (
        "https://generalmotors.wd5.myworkdayjobs.com/wday/cxs/generalmotors/Careers_GM"
        "/job/Detroit-MI/Staff-Software-Engineer_R12345"
    )
    assert detail_request.get_header("X-requested-with") == "XMLHttpRequest"
    assert detail_request.get_header("Referer") == "https://generalmotors.wd5.myworkdayjobs.com/Careers_GM"

    # Archive object names/company_slug are derived from the display name
    # (see ResponseArchive._object_key), not the YAML "key" - "gm" here.
    assert stored["object_name"].startswith("api/general_motors/")
    inserted = mock_execute_values.call_args.args[2][0]
    assert inserted[0] == "General Motors"
    assert inserted[1] == "general_motors"
    assert inserted[3] == "workday"
    assert inserted[4].adapted["jobPostings"][0]["jobPostingDetail"] == detail_payload
    assert inserted[5] == "US"


@patch.dict(os.environ, {"COMEET_TOKEN": "unit-test-token"})
@patch("scrapers.config.dbt.shutil.which", return_value="/usr/bin/dbt")
@patch("scrapers.config.dbt.subprocess.run")
@patch("scrapers.service.bronze_storage.bronze_ingest.execute_values")
@patch("scrapers.service.bronze_storage.bronze_ingest.psycopg2.connect")
@patch("scrapers.response_archive.Minio")
@patch("scrapers.service.fetch.rawfetch.urlopen")
def test_autobrains_comeet_scrape_resolves_token_from_env(
    mock_urlopen, mock_minio, mock_connect, mock_execute_values, mock_dbt, _mock_which
):
    """Comeet is the only ATS whose URL embeds a secret expanded from the
    environment (`${COMEET_TOKEN}`, see RawFetch._resolve_params) rather than
    a plain company slug - worth its own coverage since a broken expansion
    would silently leak the literal "${COMEET_TOKEN}" string into the URL."""
    stored = {}
    comeet_payload = {
        "positions": [
            {
                "uid": "pos-1",
                "name": "Autonomy Software Engineer",
                "location": {"name": "Tel Aviv"},
                "url": "https://www.comeet.com/jobs/autobrains/57.004/Autonomy-Software-Engineer/abc",
            }
        ]
    }
    mock_urlopen.return_value = _urlopen_json(comeet_payload)
    _archive_minio_client(mock_minio, stored)
    _stub_postgres(mock_connect)
    mock_dbt.return_value = MagicMock(returncode=0)

    status = main(["--company", "autobrains"])

    assert status == 0
    request = mock_urlopen.call_args[0][0]
    assert request.full_url == (
        "https://www.comeet.co/careers-api/2.0/company/57.004/positions?token=unit-test-token&details=true"
    )
    assert stored["object_name"].startswith("api/autobrains/")
    inserted = mock_execute_values.call_args.args[2][0]
    assert inserted[0] == "AutoBrains"
    assert inserted[1] == "autobrains"
    assert inserted[3] == "comeet"
    assert inserted[4].adapted == comeet_payload
    assert inserted[5] == "IL"
