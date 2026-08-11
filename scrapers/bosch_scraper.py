"""Download and normalize Bosch's public job postings from SmartRecruiters.

Run from the project root:

    python scrapers/bosch_scraper.py

By default, the scraper downloads the latest 100 public Bosch jobs and writes
them to ``data/bosch_jobs.json``. Use ``--max-jobs`` to choose a smaller or
larger batch for later project work.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


BOSCH_COMPANY_ID = "BoschGroup"
BOSCH_API_BASE = (
    f"https://api.smartrecruiters.com/v1/companies/{BOSCH_COMPANY_ID}/postings"
)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "bosch_jobs.json"
DEFAULT_MAX_JOBS = 100
PAGE_SIZE = 100
DETAIL_WORKERS = 5
USER_AGENT = "AutonomousVehicleJobProfiles/1.0 (academic job-market research)"
REQUIRED_FIELDS = (
    "company",
    "job_id",
    "job_title",
    "location",
    "description",
    "posting_date",
    "source_url",
    "collection_method",
    "ats",
    "collected_at",
)


class _HTMLTextExtractor(HTMLParser):
    """Convert the HTML fragments in SmartRecruiters job sections to text."""

    BLOCK_TAGS = {"br", "div", "li", "ol", "p", "section", "ul"}

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _clean_text(value: Any) -> str:
    if value is None:
        return ""

    text = unescape(str(value)).replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def _html_to_text(value: Any) -> str:
    if not value:
        return ""

    parser = _HTMLTextExtractor()
    parser.feed(str(value))
    parser.close()
    return _clean_text("".join(parser.parts))


def _label(value: Any) -> str:
    if isinstance(value, dict):
        return _clean_text(value.get("label"))
    return ""


def _get_json(url: str, timeout: float, retries: int = 3) -> dict[str, Any]:
    """Request one JSON object, retrying rate limits and temporary failures."""

    request = Request(
        url,
        headers={"Accept": "application/json", "User-Agent": USER_AGENT},
    )

    for attempt in range(1, retries + 1):
        try:
            with urlopen(request, timeout=timeout) as response:  # noqa: S310
                payload = json.load(response)
            if not isinstance(payload, dict):
                raise ValueError("SmartRecruiters returned an invalid JSON response.")
            return payload
        except HTTPError as exc:
            retryable = exc.code == 429 or 500 <= exc.code < 600
            if not retryable or attempt == retries:
                raise RuntimeError(
                    f"SmartRecruiters request failed with HTTP {exc.code}: {url}"
                ) from exc
            retry_after = exc.headers.get("Retry-After")
            try:
                delay = float(retry_after) if retry_after else 2 ** (attempt - 1)
            except ValueError:
                delay = 2 ** (attempt - 1)
            time.sleep(max(delay, 0.0))
        except URLError as exc:
            if attempt == retries:
                raise RuntimeError(
                    f"Could not connect to SmartRecruiters: {exc.reason}"
                ) from exc
            time.sleep(2 ** (attempt - 1))

    raise RuntimeError("SmartRecruiters request failed after all retry attempts.")


def fetch_job_summaries(max_jobs: int, timeout: float = 30.0) -> list[dict[str, Any]]:
    """Fetch the newest public posting summaries with pagination."""

    summaries: list[dict[str, Any]] = []
    offset = 0

    while len(summaries) < max_jobs:
        requested = min(PAGE_SIZE, max_jobs - len(summaries))
        query = urlencode(
            {"limit": requested, "offset": offset, "destination": "PUBLIC"}
        )
        payload = _get_json(f"{BOSCH_API_BASE}?{query}", timeout=timeout)
        page = payload.get("content")
        if not isinstance(page, list):
            raise ValueError("SmartRecruiters response did not contain a postings list.")
        if not all(isinstance(item, dict) for item in page):
            raise ValueError("SmartRecruiters returned an invalid posting summary.")

        summaries.extend(page)
        if not page:
            break

        offset += len(page)
        total_found = payload.get("totalFound")
        if isinstance(total_found, int) and offset >= total_found:
            break

    return summaries[:max_jobs]


def fetch_job_details(
    summaries: list[dict[str, Any]], timeout: float = 30.0
) -> list[dict[str, Any]]:
    """Fetch full descriptions while limiting concurrent API requests."""

    posting_ids = [_clean_text(summary.get("id")) for summary in summaries]
    if any(not posting_id for posting_id in posting_ids):
        raise ValueError("A Bosch posting summary was missing its job ID.")

    def fetch(posting_id: str) -> dict[str, Any]:
        return _get_json(f"{BOSCH_API_BASE}/{posting_id}", timeout=timeout)

    with ThreadPoolExecutor(max_workers=DETAIL_WORKERS) as executor:
        return list(executor.map(fetch, posting_ids))


def _build_description(job: dict[str, Any]) -> str:
    job_ad = job.get("jobAd")
    sections = job_ad.get("sections") if isinstance(job_ad, dict) else None
    if not isinstance(sections, dict):
        return ""

    parts: list[str] = []
    for key in (
        "companyDescription",
        "jobDescription",
        "qualifications",
        "additionalInformation",
    ):
        section = sections.get(key)
        if not isinstance(section, dict):
            continue
        title = _clean_text(section.get("title"))
        text = _html_to_text(section.get("text"))
        if text:
            parts.append(f"{title}\n{text}" if title else text)
    return "\n\n".join(parts)


def _workplace_type(location: dict[str, Any]) -> str:
    if location.get("hybrid") is True:
        return "hybrid"
    if location.get("remote") is True:
        return "remote"
    return "onsite"


def normalize_job(job: dict[str, Any], collected_at: str) -> dict[str, Any]:
    """Map one SmartRecruiters record to the shared project schema."""

    location = job.get("location")
    if not isinstance(location, dict):
        location = {}

    full_location = _clean_text(location.get("fullLocation"))
    if not full_location:
        location_parts = [
            _clean_text(location.get("city")),
            _clean_text(location.get("region")),
            _clean_text(location.get("country")),
        ]
        full_location = ", ".join(part for part in location_parts if part)

    language = job.get("language")
    language_code = (
        _clean_text(language.get("code")) if isinstance(language, dict) else ""
    )

    source_url = _clean_text(job.get("postingUrl"))
    apply_url = _clean_text(job.get("applyUrl"))
    if not source_url:
        source_url = apply_url.split("?", maxsplit=1)[0]

    function = _label(job.get("function"))

    return {
        "company": "Bosch",
        "job_id": _clean_text(job.get("id")),
        "job_title": _clean_text(job.get("name")),
        "location": full_location,
        "all_locations": [full_location] if full_location else [],
        "country_code": _clean_text(location.get("country")),
        "team": function,
        "department": _label(job.get("department")),
        "commitment": _label(job.get("typeOfEmployment")),
        "workplace_type": _workplace_type(location),
        "description": _build_description(job),
        "salary_range": None,
        "posting_date": _clean_text(job.get("releasedDate")),
        "source_url": source_url,
        "apply_url": apply_url,
        "collection_method": "API",
        "ats": "SmartRecruiters",
        "collected_at": collected_at,
        "language": language_code,
        "job_reference": _clean_text(job.get("refNumber")),
        "function": function,
        "experience_level": _label(job.get("experienceLevel")),
        "industry": _label(job.get("industry")),
    }


def validate_records(records: list[dict[str, Any]]) -> None:
    """Prevent empty, incomplete, or duplicate data from replacing good output."""

    if not records:
        raise ValueError("SmartRecruiters returned no Bosch jobs.")

    seen_job_ids: set[str] = set()
    for position, record in enumerate(records, start=1):
        missing = [field for field in REQUIRED_FIELDS if not record.get(field)]
        if missing:
            fields = ", ".join(missing)
            raise ValueError(f"Bosch job record {position} is missing: {fields}.")

        job_id = str(record["job_id"])
        if job_id in seen_job_ids:
            raise ValueError(f"SmartRecruiters returned duplicate Bosch job ID: {job_id}.")
        seen_job_ids.add(job_id)


def scrape_bosch_jobs(max_jobs: int = DEFAULT_MAX_JOBS, timeout: float = 30.0) -> list[dict[str, Any]]:
    """Fetch, normalize, and validate a batch of current Bosch jobs."""

    summaries = fetch_job_summaries(max_jobs=max_jobs, timeout=timeout)
    details = fetch_job_details(summaries, timeout=timeout)
    collected_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    records = [normalize_job(job, collected_at) for job in details]
    validate_records(records)
    return records


def write_json(records: list[dict[str, Any]], output_path: Path) -> None:
    """Write UTF-8 JSON atomically so failed runs keep the previous dataset."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(output_path.suffix + ".tmp")
    try:
        with temporary_path.open("w", encoding="utf-8", newline="\n") as file:
            json.dump(records, file, ensure_ascii=False, indent=2)
            file.write("\n")
        temporary_path.replace(output_path)
    finally:
        temporary_path.unlink(missing_ok=True)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download Bosch's public SmartRecruiters jobs as normalized JSON."
    )
    parser.add_argument(
        "--max-jobs",
        type=int,
        default=DEFAULT_MAX_JOBS,
        help=f"number of newest jobs to collect (default: {DEFAULT_MAX_JOBS})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"JSON output path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="HTTP timeout in seconds (default: 30)",
    )
    args = parser.parse_args(argv)
    if args.max_jobs < 1:
        parser.error("--max-jobs must be at least 1")
    if args.timeout <= 0:
        parser.error("--timeout must be greater than 0")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        records = scrape_bosch_jobs(max_jobs=args.max_jobs, timeout=args.timeout)
        write_json(records, args.output)
    except (RuntimeError, ValueError) as exc:
        print(f"Bosch scraper failed: {exc}", file=sys.stderr)
        return 1

    print(f"Saved {len(records)} Bosch jobs to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

