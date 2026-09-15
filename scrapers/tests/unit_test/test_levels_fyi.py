from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

from scrapers.service.silver_cleaning.levels_fyi import (
    LevelsFyiAverage,
    fetch_company_average,
)

# A trimmed real excerpt of the markdown format fetched live from
# https://www.levels.fyi/companies/waymo/salaries.md this session.
_WAYMO_MARKDOWN = """# Levels.fyi – Waymo Salaries

**URL:** https://www.levels.fyi/companies/waymo/salaries
**Generated:** 2026-09-14T12:49:08.736Z
**Scope:** All roles at Waymo in United States
**Location:** United States
**Currency:** USD ($)

---
## Summary
Waymo's salary ranges from $59,623 in total compensation per year for a Information Technologist (IT) at the low-end to $899,833 for a Software Engineer at the high-end.

---
## Aggregate Highlights
- Median Total Compensation (All Roles): $330,413

| Rank | Job Family | Median Total Compensation |
| --- | --- | --- |
| 1 | Software Engineer | $429,217 |
"""


def _mock_response(body: bytes):
    mock = MagicMock()
    mock.read.return_value = body
    mock.__enter__.return_value = mock
    mock.__exit__.return_value = False
    return mock


@patch("scrapers.service.silver_cleaning.levels_fyi.urlopen")
def test_parses_median_total_compensation_and_currency(mock_urlopen):
    mock_urlopen.return_value = _mock_response(_WAYMO_MARKDOWN.encode("utf-8"))

    result = fetch_company_average("waymo")

    assert result == LevelsFyiAverage(
        median_total_compensation=330413.0,
        currency="USD",
        source_url="https://www.levels.fyi/companies/waymo/salaries.md",
    )


@patch("scrapers.service.silver_cleaning.levels_fyi.urlopen")
def test_sends_realistic_browser_headers(mock_urlopen):
    mock_urlopen.return_value = _mock_response(_WAYMO_MARKDOWN.encode("utf-8"))

    fetch_company_average("waymo")

    request = mock_urlopen.call_args.args[0]
    assert request.get_header("User-agent").startswith("Mozilla/5.0")
    assert "text/markdown" in request.get_header("Accept")


@patch("scrapers.service.silver_cleaning.levels_fyi.urlopen")
def test_returns_none_on_404(mock_urlopen):
    mock_urlopen.side_effect = HTTPError(
        url="https://www.levels.fyi/companies/does-not-exist/salaries.md",
        code=404,
        msg="Not Found",
        hdrs=None,
        fp=None,
    )

    assert fetch_company_average("does-not-exist") is None


@patch("scrapers.service.silver_cleaning.levels_fyi.urlopen")
def test_returns_none_when_median_line_missing(mock_urlopen):
    mock_urlopen.return_value = _mock_response(b"# Some unrelated page\nNo salary data here.")

    assert fetch_company_average("mystery-co") is None
