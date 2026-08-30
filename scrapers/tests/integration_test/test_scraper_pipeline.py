import json
from io import BytesIO
from unittest.mock import MagicMock, patch

from scrapers.scraper_main import main
from scrapers.utils.company_registry import CompanyRegistry


def _urlopen_json(payload):
    mock_response = MagicMock()
    mock_response.__enter__.return_value = BytesIO(
        json.dumps(payload).encode("utf-8")
    )
    mock_response.__exit__.return_value = False
    return mock_response


def test_registry_loads_checked_in_company_list():
    companies = CompanyRegistry.load_company_list()
    keys = {row["key"] for row in companies}

    assert "stack_av" in keys
    assert "waabi" in keys
    waabi = next(row for row in companies if row["key"] == "waabi")
    assert waabi["ats"] == "lever"
    assert waabi["slug"] == "waabi"


def test_enabled_api_sources_uses_enabled_flag_from_real_yaml():
    companies = CompanyRegistry.load_company_list()
    selected = CompanyRegistry.enabled_api_sources(companies)
    selected_keys = {row["key"] for row in selected}
    enabled_api = {
        row["key"]
        for row in companies
        if row.get("enabled") and row.get("ats") in CompanyRegistry.API_ATS
    }

    assert "stack_av" in selected_keys
    assert selected_keys == enabled_api
    disabled = [row["key"] for row in companies if not row.get("enabled")]
    assert not any(key in selected_keys for key in disabled)


@patch("scrapers.response_archive.Minio")
@patch("scrapers.strategy.apistrategy.urlopen")
def test_stack_av_scrape_archives_greenhouse_payload(mock_urlopen, mock_minio):
    stored = {}

    def put_object(**kwargs):
        stored["object_name"] = kwargs["object_name"]
        stored["bucket"] = kwargs["bucket_name"]
        stored["bytes"] = kwargs["data"].read()

    mock_urlopen.return_value = _urlopen_json(
        {
            "jobs": [
                {"id": "101", "title": "Software Engineer"},
                {"id": "102", "title": "ML Engineer"},
            ],
            "meta": {"total": 2},
        }
    )
    client = mock_minio.return_value
    client.bucket_exists.return_value = False
    client.put_object.side_effect = put_object

    status = main(["--company", "stack_av", "--max-jobs", "1"])

    assert status == 0
    request = mock_urlopen.call_args[0][0]
    assert request.get_header("User-agent") == "Mozilla/5.0"
    assert request.full_url.endswith("/boards/stackav/jobs")
    assert stored["object_name"].startswith("api/stack_av/")
    assert stored["object_name"].endswith(".parquet")
    client.make_bucket.assert_called_once()


@patch("scrapers.response_archive.Minio")
@patch("scrapers.strategy.apistrategy.urlopen")
def test_ashby_http_403_is_recorded_without_aborting_process(mock_urlopen, mock_minio):
    from urllib.error import HTTPError

    mock_urlopen.side_effect = HTTPError(
        url="https://api.ashbyhq.com/posting-api/job-board/42dot",
        code=403,
        msg="Forbidden",
        hdrs=None,
        fp=None,
    )

    status = main(["--company", "fortytwo_dot", "--max-jobs", "1"])

    assert status == 1
    mock_minio.return_value.put_object.assert_not_called()
