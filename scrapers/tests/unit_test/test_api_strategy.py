import json
from io import BytesIO
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

import pytest

from scrapers.strategy.apistrategy import APIStrategy


def _urlopen_json(payload):
    mock_response = MagicMock()
    mock_response.__enter__.return_value = BytesIO(
        json.dumps(payload).encode("utf-8")
    )
    mock_response.__exit__.return_value = False
    return mock_response


def test_extract_jobs_from_greenhouse_and_ashby_payload():
    strategy = APIStrategy("greenhouse", "stackav", "Stack AV")
    jobs = strategy._extract_jobs(
        {"jobs": [{"id": "1", "title": "Engineer"}], "meta": {"total": 1}}
    )

    assert jobs == [{"id": "1", "title": "Engineer"}]


def test_extract_jobs_from_lever_list():
    strategy = APIStrategy("lever", "waabi", "Waabi")
    jobs = strategy._extract_jobs([{"id": "abc", "text": "Engineer"}])

    assert jobs[0]["id"] == "abc"


def test_extract_jobs_from_smartrecruiters_content():
    strategy = APIStrategy("smartrecruiters", "BoschGroup", "Bosch")
    jobs = strategy._extract_jobs({"content": [{"id": "sr-1"}]})

    assert jobs == [{"id": "sr-1"}]


def test_extract_jobs_rejects_greenhouse_count_mismatch():
    strategy = APIStrategy("greenhouse", "stackav", "Stack AV")

    with pytest.raises(ValueError, match="reported 2 jobs"):
        strategy._extract_jobs({"jobs": [{"id": "1"}], "meta": {"total": 2}})


def test_unknown_ats_raises_before_fetch(tmp_path, monkeypatch):
    sources = tmp_path / "ats_sources.yaml"
    sources.write_text("ats_sources:\n  greenhouse:\n    api_base: https://example/{slug}\n")
    monkeypatch.setattr("scrapers.strategy.apistrategy.ATS_PATH", str(sources))
    strategy = APIStrategy("not-an-ats", "slug", "Example")

    with pytest.raises(ValueError, match="not available"):
        strategy.fetch_postings(max_jobs=1)


@patch("scrapers.strategy.apistrategy.ResponseArchive")
@patch("scrapers.strategy.apistrategy.urlopen")
def test_fetch_postings_sends_user_agent_and_limits_jobs(
    mock_urlopen, mock_archive, tmp_path, monkeypatch
):
    sources = tmp_path / "ats_sources.yaml"
    sources.write_text(
        "ats_sources:\n"
        "  greenhouse:\n"
        "    api_base: https://boards-api.greenhouse.io/v1/boards/{slug}/jobs\n"
    )
    monkeypatch.setattr("scrapers.strategy.apistrategy.ATS_PATH", str(sources))
    mock_urlopen.return_value = _urlopen_json(
        {
            "jobs": [{"id": "1"}, {"id": "2"}, {"id": "3"}],
            "meta": {"total": 3},
        }
    )
    mock_archive.return_value.save_raw_response.return_value = "api/stack_av/file.parquet"

    strategy = APIStrategy("greenhouse", "stackav", "Stack AV")
    jobs = strategy.fetch_postings(max_jobs=2)

    assert [job["id"] for job in jobs] == ["1", "2"]
    request = mock_urlopen.call_args[0][0]
    assert request.get_header("User-agent") == "Mozilla/5.0"
    assert "stackav" in request.full_url
    mock_archive.return_value.save_raw_response.assert_called_once()


@patch("scrapers.strategy.apistrategy.urlopen")
def test_fetch_api_json_data_maps_http_403_to_runtime_error(mock_urlopen):
    mock_urlopen.side_effect = HTTPError(
        url="https://api.ashbyhq.com/posting-api/job-board/42dot",
        code=403,
        msg="Forbidden",
        hdrs=None,
        fp=None,
    )
    strategy = APIStrategy("ashby", "42dot", "42dot")

    with pytest.raises(RuntimeError, match="HTTP 403"):
        strategy.fetch_api_json_data("https://api.ashbyhq.com/posting-api/job-board/42dot")
