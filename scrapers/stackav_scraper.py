"""Download and normalize Stack AV's public job postings from Greenhouse.

Run from the project root:

    python scrapers/stackav_scraper.py

The normalized records are written to ``data/stackav_jobs.json`` by default.
Only published job-advertisement data is requested; this scraper does not
submit applications or collect applicant information.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


STACKAV_API_URL = (
    "https://boards-api.greenhouse.io/v1/boards/stackav/jobs?content=true"
)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "stackav_jobs.json"
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
    """Convert Greenhouse's encoded HTML descriptions into readable text."""

    BLOCK_TAGS = {"br", "div", "h1", "h2", "h3", "li", "ol", "p", "section", "ul"}

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

    decoded = str(value)
    for _ in range(3):
        next_value = unescape(decoded)
        if next_value == decoded:
            break
        decoded = next_value

    parser = _HTMLTextExtractor()
    parser.feed(decoded)
    parser.close()
    return _clean_text("".join(parser.parts))


def _get_json(timeout: float, retries: int = 3) -> dict[str, Any]:
    """Fetch the public Stack AV board with temporary-failure retries."""

    request = Request(
        STACKAV_API_URL,
        headers={"Accept": "application/json", "User-Agent": USER_AGENT},
    )

    for attempt in range(1, retries + 1):
        try:
            with urlopen(request, timeout=timeout) as response:  # noqa: S310
                payload = json.load(response)
            if not isinstance(payload, dict):
                raise ValueError("Greenhouse returned an invalid JSON response.")
            return payload
        except HTTPError as exc:
            retryable = exc.code == 429 or 500 <= exc.code < 600
            if not retryable or attempt == retries:
                raise RuntimeError(
                    f"Greenhouse request failed with HTTP {exc.code}."
                ) from exc
            retry_after = exc.headers.get("Retry-After")
            try:
                delay = float(retry_after) if retry_after else 2 ** (attempt - 1)
            except ValueError:
                delay = 2 ** (attempt - 1)
            time.sleep(max(delay, 0.0))
        except URLError as exc:
            if attempt == retries:
                raise RuntimeError(f"Could not connect to Greenhouse: {exc.reason}") from exc
            time.sleep(2 ** (attempt - 1))

    raise RuntimeError("Greenhouse request failed after all retry attempts.")


def fetch_jobs(timeout: float = 30.0) -> list[dict[str, Any]]:
    """Fetch every currently published Stack AV posting with full content."""

    payload = _get_json(timeout=timeout)
    jobs = payload.get("jobs")
    if not isinstance(jobs, list):
        raise ValueError("Greenhouse response did not contain a jobs list.")
    if not all(isinstance(job, dict) for job in jobs):
        raise ValueError("Greenhouse returned an invalid Stack AV job record.")

    meta = payload.get("meta")
    total = meta.get("total") if isinstance(meta, dict) else None
    if isinstance(total, int) and total != len(jobs):
        raise ValueError(
            f"Greenhouse reported {total} jobs but returned {len(jobs)} records."
        )
    return jobs


def _names(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []

    result: list[str] = []
    for value in values:
        if not isinstance(value, dict):
            continue
        name = _clean_text(value.get("name"))
        if name and name not in result:
            result.append(name)
    return result


def _workplace_type(location: str, offices: list[str]) -> str:
    searchable = " ".join([location, *offices]).casefold()
    if "hybrid" in searchable:
        return "hybrid"
    if "remote" in searchable:
        return "remote"
    return "onsite"


def normalize_job(job: dict[str, Any], collected_at: str) -> dict[str, Any]:
    """Map one Greenhouse record to the shared project schema."""

    location_value = job.get("location")
    location = (
        _clean_text(location_value.get("name"))
        if isinstance(location_value, dict)
        else ""
    )
    departments = _names(job.get("departments"))
    offices = _names(job.get("offices"))
    source_url = _clean_text(job.get("absolute_url"))

    return {
        "company": "Stack AV",
        "job_id": _clean_text(job.get("id")),
        "job_title": _clean_text(job.get("title")),
        "location": location,
        "all_locations": [location] if location else [],
        "country_code": "",
        "team": departments[0] if departments else "",
        "department": ", ".join(departments),
        "commitment": "",
        "workplace_type": _workplace_type(location, offices),
        "description": _html_to_text(job.get("content")),
        "salary_range": None,
        "posting_date": _clean_text(job.get("first_published")),
        "source_url": source_url,
        "apply_url": source_url,
        "collection_method": "API",
        "ats": "Greenhouse",
        "collected_at": collected_at,
        "language": _clean_text(job.get("language")),
        "job_reference": _clean_text(job.get("requisition_id")),
        "internal_job_id": _clean_text(job.get("internal_job_id")),
        "updated_at": _clean_text(job.get("updated_at")),
        "application_deadline": _clean_text(job.get("application_deadline")),
        "offices": offices,
    }


def validate_records(records: list[dict[str, Any]]) -> None:
    """Prevent empty, incomplete, or duplicate data from replacing good output."""

    if not records:
        raise ValueError("Greenhouse returned no Stack AV jobs.")

    seen_job_ids: set[str] = set()
    for position, record in enumerate(records, start=1):
        missing = [field for field in REQUIRED_FIELDS if not record.get(field)]
        if missing:
            fields = ", ".join(missing)
            raise ValueError(f"Stack AV job record {position} is missing: {fields}.")

        job_id = str(record["job_id"])
        if job_id in seen_job_ids:
            raise ValueError(f"Greenhouse returned duplicate Stack AV job ID: {job_id}.")
        seen_job_ids.add(job_id)


def scrape_stackav_jobs(timeout: float = 30.0) -> list[dict[str, Any]]:
    """Fetch, normalize, sort, and validate current Stack AV jobs."""

    collected_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    records = [normalize_job(job, collected_at) for job in fetch_jobs(timeout=timeout)]
    records.sort(key=lambda record: record["posting_date"], reverse=True)
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
        description="Download Stack AV's published Greenhouse jobs as normalized JSON."
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
    if args.timeout <= 0:
        parser.error("--timeout must be greater than 0")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        records = scrape_stackav_jobs(timeout=args.timeout)
        write_json(records, args.output)
    except (RuntimeError, ValueError) as exc:
        print(f"Stack AV scraper failed: {exc}", file=sys.stderr)
        return 1

    print(f"Saved {len(records)} Stack AV jobs to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

