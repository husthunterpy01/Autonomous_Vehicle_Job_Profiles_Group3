from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# A bare/default urllib request (no User-Agent, no Accept) gets a 200 with an
# empty body from levels.fyi - confirmed live this session. A realistic
# browser-style header set is required to get the actual markdown content.
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
_HEADERS = {"User-Agent": _USER_AGENT, "Accept": "text/markdown,text/plain,*/*"}

_MEDIAN_RE = re.compile(r"Median Total Compensation \(All Roles\):\s*\$?([\d,]+)")
_CURRENCY_RE = re.compile(r"\*\*Currency:\*\*\s*(\w+)")


@dataclass(frozen=True)
class LevelsFyiAverage:
    """A company-wide median from levels.fyi.

    This is TOTAL compensation (base salary + annualized stock + bonus),
    not base salary, and a single company-wide median across all roles and
    levels - it is not tied to any specific job posting or level. Callers
    must tag data derived from this as an estimate (e.g.
    salary_source="levels_fyi_average") and never present it as a real
    posting's disclosed base salary range.
    """

    median_total_compensation: float
    currency: str
    source_url: str


def fetch_company_average(slug: str, timeout: float = 15.0) -> LevelsFyiAverage | None:
    """Fetch and parse levels.fyi's per-company salary summary page.

    Returns None if the company has no page on levels.fyi (404) or the
    response can't be parsed - never raises for an unknown/missing company,
    since this is a best-effort fallback, not a required data source.

    Note: robots.txt could not be cleanly checked this session (the fetch
    returned compressed/binary content this tool couldn't decode) - worth a
    manual check of levels.fyi's terms/robots.txt before relying on this at
    any real scale.
    """
    url = f"https://www.levels.fyi/companies/{slug}/salaries.md"
    request = Request(url, headers=_HEADERS)
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        if exc.code == 404:
            return None
        raise
    except URLError:
        return None

    median_match = _MEDIAN_RE.search(body)
    if not median_match:
        return None
    currency_match = _CURRENCY_RE.search(body)
    currency = currency_match.group(1).upper() if currency_match else "USD"

    return LevelsFyiAverage(
        median_total_compensation=float(median_match.group(1).replace(",", "")),
        currency=currency,
        source_url=url,
    )
