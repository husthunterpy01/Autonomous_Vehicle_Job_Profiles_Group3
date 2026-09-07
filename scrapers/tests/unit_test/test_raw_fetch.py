import json
from io import BytesIO
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

import pytest

from scrapers.service.fetch.rawfetch import RawFetch


def _urlopen_body(payload, content_type="application/json", status=200):
    body = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")
    mock_response = MagicMock()
    mock_response.read.return_value = body
    mock_response.status = status
    mock_response.getcode.return_value = status
    mock_response.headers = {"Content-Type": content_type}
    mock_response.__enter__.return_value = mock_response
    mock_response.__exit__.return_value = False
    return mock_response


def test_from_company_builds_api_url(tmp_path, monkeypatch):
    sources = tmp_path / "ats_sources.yaml"
    sources.write_text(
        "ats_sources:\n"
        "  greenhouse:\n"
        "    api_base: https://boards-api.greenhouse.io/v1/boards/{slug}/jobs\n"
    )
    monkeypatch.setattr("scrapers.service.fetch.rawfetch.ATS_PATH", str(sources))
    fetcher, url = RawFetch.from_company(
        {"name": "Stack AV", "ats": "greenhouse", "slug": "stackav"}
    )

    assert fetcher.source == "api"
    assert fetcher.source_system == "greenhouse"
    assert url.endswith("/boards/stackav/jobs")


def test_from_company_uses_career_url_for_html():
    fetcher, url = RawFetch.from_company(
        {"name": "Waymo", "ats": "html", "url": "https://careers.withwaymo.com/"}
    )

    assert fetcher.source == "html"
    assert url == "https://careers.withwaymo.com/"


def test_unknown_ats_raises_before_fetch(tmp_path, monkeypatch):
    sources = tmp_path / "ats_sources.yaml"
    sources.write_text("ats_sources:\n  greenhouse:\n    api_base: https://example/{slug}\n")
    monkeypatch.setattr("scrapers.service.fetch.rawfetch.ATS_PATH", str(sources))

    with pytest.raises(ValueError, match="not available"):
        RawFetch.from_company({"name": "Example", "ats": "not-an-ats", "slug": "slug"})


@patch("scrapers.service.fetch.rawfetch.ResponseArchive")
@patch("scrapers.service.fetch.rawfetch.urlopen")
def test_fetch_and_archive_saves_raw_json(mock_urlopen, mock_archive, tmp_path, monkeypatch):
    sources = tmp_path / "ats_sources.yaml"
    sources.write_text(
        "ats_sources:\n"
        "  greenhouse:\n"
        "    api_base: https://boards-api.greenhouse.io/v1/boards/{slug}/jobs\n"
    )
    monkeypatch.setattr("scrapers.service.fetch.rawfetch.ATS_PATH", str(sources))
    payload = {"jobs": [{"id": "1"}, {"id": "2"}], "meta": {"total": 2}}
    mock_urlopen.return_value = _urlopen_body(payload)
    mock_archive.return_value.save_raw_response.return_value = "api/stack_av/file.parquet"

    fetcher, url = RawFetch.from_company(
        {"name": "Stack AV", "ats": "greenhouse", "slug": "stackav"}
    )
    object_key = fetcher.fetch_and_archive(url, timeout=5)

    assert object_key == "api/stack_av/file.parquet"
    request = mock_urlopen.call_args[0][0]
    assert request.get_header("User-agent") == "Mozilla/5.0"
    saved = mock_archive.return_value.save_raw_response.call_args.kwargs
    assert saved["source"] == "api"
    assert saved["source_system"] == "greenhouse"
    assert json.loads(saved["raw_response"]) == payload


@patch("scrapers.service.fetch.rawfetch.ResponseArchive")
@patch("scrapers.service.fetch.rawfetch.urlopen")
def test_fetch_and_archive_saves_raw_html(mock_urlopen, mock_archive):
    html = b"<html><body>Careers</body></html>"
    mock_urlopen.return_value = _urlopen_body(html, content_type="text/html")
    mock_archive.return_value.save_raw_response.return_value = "html/waymo/file.parquet"

    fetcher = RawFetch("Waymo", "html", "html")
    fetcher.fetch_and_archive("https://careers.withwaymo.com/")

    saved = mock_archive.return_value.save_raw_response.call_args.kwargs
    assert saved["source"] == "html"
    assert saved["raw_response"] == html
    assert saved["content_type"] == "text/html"


@patch("scrapers.service.fetch.rawfetch.time.sleep")
@patch("scrapers.service.fetch.rawfetch.ResponseArchive")
@patch("scrapers.service.fetch.rawfetch.urlopen")
def test_fetch_and_archive_expands_smartrecruiters_details(
    mock_urlopen, mock_archive, mock_sleep
):
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
        "typeOfEmployment": {"label": "Full-time"},
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
        _urlopen_body(list_payload),
        _urlopen_body(detail_payload),
    ]
    mock_archive.return_value.save_raw_response.return_value = "api/bosch/file.parquet"
    fetcher = RawFetch("Bosch", "api", "smartrecruiters")
    list_url = "https://api.smartrecruiters.com/v1/companies/BoschGroup/postings"

    fetcher.fetch_and_archive(list_url, timeout=5)

    urls = [call.args[0].full_url for call in mock_urlopen.call_args_list]
    assert urls == [
        list_url,
        f"{list_url}/744000146470121",
    ]
    saved = mock_archive.return_value.save_raw_response.call_args.kwargs
    archived = saved["raw_response"]
    assert archived["content"][0]["jobAd"]["sections"]["jobDescription"]["text"] == (
        "<p>Release product documents</p>"
    )


@patch("scrapers.service.fetch.rawfetch.time.sleep")
@patch("scrapers.service.fetch.rawfetch.ResponseArchive")
@patch("scrapers.service.fetch.rawfetch.urlopen")
def test_smartrecruiters_keeps_list_item_when_detail_fails(
    mock_urlopen, mock_archive, mock_sleep
):
    list_payload = {"content": [{"id": "missing", "name": "Fallback Role"}]}
    mock_urlopen.side_effect = [
        _urlopen_body(list_payload),
        HTTPError(
            url="https://api.smartrecruiters.com/v1/companies/BoschGroup/postings/missing",
            code=404,
            msg="Not Found",
            hdrs=None,
            fp=None,
        ),
    ]
    mock_archive.return_value.save_raw_response.return_value = "api/bosch/file.parquet"
    fetcher = RawFetch("Bosch", "api", "smartrecruiters")

    fetcher.fetch_and_archive(
        "https://api.smartrecruiters.com/v1/companies/BoschGroup/postings"
    )

    archived = mock_archive.return_value.save_raw_response.call_args.kwargs["raw_response"]
    assert archived["content"][0]["name"] == "Fallback Role"
    assert "jobAd" not in archived["content"][0]


def test_from_company_collects_lever_fallback_urls(tmp_path, monkeypatch):
    sources = tmp_path / "ats_sources.yaml"
    sources.write_text(
        "ats_sources:\n"
        "  lever:\n"
        "    api_base: https://api.lever.co/v0/postings/{slug}\n"
        "    api_base_v2: https://api.eu.lever.co/v0/postings/{slug}?mode=json\n"
    )
    monkeypatch.setattr("scrapers.service.fetch.rawfetch.ATS_PATH", str(sources))

    fetcher, url = RawFetch.from_company(
        {"name": "Nuro", "ats": "lever", "slug": "nuro"}
    )

    assert url == "https://api.lever.co/v0/postings/nuro"
    assert fetcher.fallback_urls == [
        "https://api.eu.lever.co/v0/postings/nuro?mode=json"
    ]


@patch("scrapers.service.fetch.rawfetch.ResponseArchive")
@patch("scrapers.service.fetch.rawfetch.urlopen")
def test_fetch_and_archive_switches_to_fallback_url(mock_urlopen, mock_archive):
    payload = {"postings": [{"id": "1"}]}
    mock_urlopen.side_effect = [
        HTTPError(
            url="https://api.lever.co/v0/postings/nuro",
            code=404,
            msg="Not Found",
            hdrs=None,
            fp=None,
        ),
        _urlopen_body(payload),
    ]
    mock_archive.return_value.save_raw_response.return_value = "api/nuro/file.parquet"

    fetcher = RawFetch(
        "Nuro",
        "api",
        "lever",
        fallback_urls=["https://api.eu.lever.co/v0/postings/nuro?mode=json"],
    )
    object_key = fetcher.fetch_and_archive(
        "https://api.lever.co/v0/postings/nuro", timeout=5
    )

    assert object_key == "api/nuro/file.parquet"
    assert mock_urlopen.call_count == 2
    fetched_url = mock_urlopen.call_args_list[1][0][0].full_url
    assert fetched_url == "https://api.eu.lever.co/v0/postings/nuro?mode=json"
    saved = mock_archive.return_value.save_raw_response.call_args.kwargs
    assert json.loads(saved["raw_response"]) == payload


@patch("scrapers.service.fetch.rawfetch.ResponseArchive")
@patch("scrapers.service.fetch.rawfetch.urlopen")
def test_fetch_and_archive_raises_when_all_urls_fail(mock_urlopen, mock_archive):
    mock_urlopen.side_effect = HTTPError(
        url="https://api.lever.co/v0/postings/nuro",
        code=404,
        msg="Not Found",
        hdrs=None,
        fp=None,
    )
    fetcher = RawFetch(
        "Nuro",
        "api",
        "lever",
        fallback_urls=["https://api.eu.lever.co/v0/postings/nuro?mode=json"],
    )

    with pytest.raises(RuntimeError, match="HTTP 404"):
        fetcher.fetch_and_archive("https://api.lever.co/v0/postings/nuro")
    mock_archive.return_value.save_raw_response.assert_not_called()


def _workday_sources(tmp_path, monkeypatch):
    sources = tmp_path / "ats_sources.yaml"
    sources.write_text(
        "ats_sources:\n"
        "  workday:\n"
        "    api_base: https://{host}/wday/cxs/{tenant}/{site}/jobs\n"
        "    method: POST\n"
        '    body: \'{"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": ""}\'\n'
    )
    monkeypatch.setattr("scrapers.service.fetch.rawfetch.ATS_PATH", str(sources))


def test_from_company_builds_workday_post_request(tmp_path, monkeypatch):
    _workday_sources(tmp_path, monkeypatch)

    fetcher, url = RawFetch.from_company(
        {
            "name": "General Motors",
            "ats": "workday",
            "slug": None,
            "params": {
                "host": "generalmotors.wd5.myworkdayjobs.com",
                "tenant": "generalmotors",
                "site": "Careers_GM",
            },
        }
    )

    assert url == (
        "https://generalmotors.wd5.myworkdayjobs.com/wday/cxs/generalmotors/Careers_GM/jobs"
    )
    assert fetcher.request_method == "POST"
    assert json.loads(fetcher.request_body) == {
        "appliedFacets": {},
        "limit": 20,
        "offset": 0,
        "searchText": "",
    }


@patch("scrapers.service.fetch.rawfetch.ResponseArchive")
@patch("scrapers.service.fetch.rawfetch.time.sleep")
@patch("scrapers.service.fetch.rawfetch.urlopen")
def test_fetch_and_archive_posts_pages_and_expands_workday(
    mock_urlopen, _mock_sleep, mock_archive, tmp_path, monkeypatch
):
    _workday_sources(tmp_path, monkeypatch)
    mock_urlopen.side_effect = [
        _urlopen_body(
            {
                "total": 3,
                "jobPostings": [
                    {"id": "1", "externalPath": "/job/a"},
                    {"id": "2", "externalPath": "/job/b"},
                ],
            }
        ),
        _urlopen_body({"total": 3, "jobPostings": [{"id": "3", "externalPath": "/job/c"}]}),
        _urlopen_body({"jobPostingInfo": {"jobDescription": "<p>A</p>"}}),
        _urlopen_body({"jobPostingInfo": {"jobDescription": "<p>B</p>"}}),
        _urlopen_body({"jobPostingInfo": {"jobDescription": "<p>C</p>"}}),
    ]
    mock_archive.return_value.save_raw_response.return_value = "api/general_motors/f.parquet"

    fetcher, url = RawFetch.from_company(
        {
            "name": "General Motors",
            "ats": "workday",
            "slug": None,
            "params": {
                "host": "generalmotors.wd5.myworkdayjobs.com",
                "tenant": "generalmotors",
                "site": "Careers_GM",
            },
        }
    )
    fetcher.fetch_and_archive(url, timeout=5)

    requests = [call[0][0] for call in mock_urlopen.call_args_list]
    # First two calls page the list endpoint with POST.
    assert requests[0].method == "POST"
    assert requests[0].get_header("Content-type") == "application/json"
    assert json.loads(requests[0].data)["offset"] == 0
    assert json.loads(requests[1].data)["offset"] == 2
    # Remaining calls GET the detail endpoint at the CXS base + externalPath.
    assert [r.method for r in requests[2:]] == ["GET", "GET", "GET"]
    assert [r.full_url for r in requests[2:]] == [
        "https://generalmotors.wd5.myworkdayjobs.com/wday/cxs/generalmotors/Careers_GM/job/a",
        "https://generalmotors.wd5.myworkdayjobs.com/wday/cxs/generalmotors/Careers_GM/job/b",
        "https://generalmotors.wd5.myworkdayjobs.com/wday/cxs/generalmotors/Careers_GM/job/c",
    ]

    saved = mock_archive.return_value.save_raw_response.call_args.kwargs
    postings = saved["raw_response"]["jobPostings"]
    assert [p["id"] for p in postings] == ["1", "2", "3"]
    assert [
        p["jobPostingDetail"]["jobPostingInfo"]["jobDescription"] for p in postings
    ] == ["<p>A</p>", "<p>B</p>", "<p>C</p>"]


@patch("scrapers.service.fetch.rawfetch.ResponseArchive")
@patch("scrapers.service.fetch.rawfetch.time.sleep")
@patch("scrapers.service.fetch.rawfetch.urlopen")
def test_workday_keeps_posting_when_detail_fails(
    mock_urlopen, _mock_sleep, mock_archive, tmp_path, monkeypatch
):
    _workday_sources(tmp_path, monkeypatch)
    mock_urlopen.side_effect = [
        _urlopen_body(
            {"total": 1, "jobPostings": [{"id": "1", "externalPath": "/job/a"}]}
        ),
        HTTPError(
            url="https://generalmotors.wd5.myworkdayjobs.com/wday/cxs/generalmotors/Careers_GM/job/a",
            code=404,
            msg="Not Found",
            hdrs=None,
            fp=None,
        ),
    ]
    mock_archive.return_value.save_raw_response.return_value = "api/general_motors/f.parquet"

    fetcher = RawFetch(
        "General Motors",
        "api",
        "workday",
        request_method="POST",
        request_body=b'{"limit": 20, "offset": 0}',
    )
    fetcher.fetch_and_archive(
        "https://generalmotors.wd5.myworkdayjobs.com/wday/cxs/generalmotors/Careers_GM/jobs",
        timeout=5,
    )

    postings = mock_archive.return_value.save_raw_response.call_args.kwargs[
        "raw_response"
    ]["jobPostings"]
    assert postings[0]["id"] == "1"
    assert "jobPostingDetail" not in postings[0]


@patch("scrapers.service.fetch.rawfetch.ResponseArchive")
@patch("scrapers.service.fetch.rawfetch.urlopen")
def test_fetch_and_archive_raises_on_http_403(mock_urlopen, mock_archive):
    mock_urlopen.side_effect = HTTPError(
        url="https://api.ashbyhq.com/posting-api/job-board/42dot",
        code=403,
        msg="Forbidden",
        hdrs=None,
        fp=None,
    )
    fetcher = RawFetch("42dot", "api", "ashby")

    with pytest.raises(RuntimeError, match="HTTP 403"):
        fetcher.fetch_and_archive("https://api.ashbyhq.com/posting-api/job-board/42dot")
