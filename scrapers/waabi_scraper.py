
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


WAABI_API_URL = "https://api.lever.co/v0/postings/waabi?mode=json"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "waabi_jobs.json"
USER_AGENT = "AutonomousVehicleJobProfiles/1.0 (academic job-market research)"
REQUIRED_FIELDS = (
    "company",
    "job_id",
    "job_title",
    "description",
    "source_url",
    "collection_method",
    "ats",
    "collected_at",
)


class _HTMLTextExtractor(HTMLParser):
    """Small standard-library fallback for converting Lever HTML to text."""

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _clean_text(value: Any) -> str:
    """Return readable, consistently spaced plain text."""

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
    return _clean_text(" ".join(parser.parts))


def _timestamp_to_iso8601(value: Any) -> str | None:
    """Convert Lever's optional millisecond timestamp without inventing a date."""

    if not isinstance(value, (int, float)):
        return None

    try:
        result = datetime.fromtimestamp(value / 1000, tz=timezone.utc)
    except (OSError, OverflowError, ValueError):
        return None
    return result.isoformat().replace("+00:00", "Z")


def fetch_jobs(timeout: float = 30.0, retries: int = 3) -> list[dict[str, Any]]:
    """Fetch Waabi jobs, retrying temporary network and server failures."""

    request = Request(
        WAABI_API_URL,
        headers={"Accept": "application/json", "User-Agent": USER_AGENT},
    )

    for attempt in range(1, retries + 1):
        try:
            with urlopen(request, timeout=timeout) as response:  # noqa: S310
                payload = json.load(response)
            if not isinstance(payload, list):
                raise ValueError("Lever returned JSON, but the top-level value was not a list.")
            if not all(isinstance(job, dict) for job in payload):
                raise ValueError("Lever returned a list containing an invalid job record.")
            return payload
        except HTTPError as exc:
            retryable = exc.code == 429 or 500 <= exc.code < 600
            if not retryable or attempt == retries:
                raise RuntimeError(f"Lever request failed with HTTP {exc.code}.") from exc
        except URLError as exc:
            if attempt == retries:
                raise RuntimeError(f"Could not connect to Lever: {exc.reason}") from exc

        time.sleep(2 ** (attempt - 1))

    raise RuntimeError("Lever request failed after all retry attempts.")


def normalize_job(job: dict[str, Any], collected_at: str) -> dict[str, Any]:
    """Map one Lever record to the project's shared job schema."""

    categories = job.get("categories")
    if not isinstance(categories, dict):
        categories = {}

    all_locations = categories.get("allLocations")
    if not isinstance(all_locations, list):
        all_locations = []
    all_locations = [_clean_text(location) for location in all_locations if location]

    description = _clean_text(job.get("descriptionPlain"))
    if not description:
        description = _html_to_text(job.get("description"))

    location = _clean_text(categories.get("location"))
    if not location and all_locations:
        location = ", ".join(all_locations)

    salary_range = job.get("salaryRange")
    if not isinstance(salary_range, dict):
        salary_range = None

    return {
        "company": "Waabi",
        "job_id": _clean_text(job.get("id")),
        "job_title": _clean_text(job.get("text")),
        "location": location,
        "all_locations": all_locations,
        "team": _clean_text(categories.get("team")),
        "department": _clean_text(categories.get("department")),
        "commitment": _clean_text(categories.get("commitment")),
        "workplace_type": _clean_text(job.get("workplaceType")),
        "description": description,
        "salary_range": salary_range,
        "posting_date": _timestamp_to_iso8601(job.get("createdAt")),
        "source_url": _clean_text(job.get("hostedUrl")),
        "apply_url": _clean_text(job.get("applyUrl")),
        "collection_method": "API",
        "ats": "Lever",
        "collected_at": collected_at,
    }


def validate_records(records: list[dict[str, Any]]) -> None:
    """Fail clearly instead of saving incomplete or duplicated job data."""

    if not records:
        raise ValueError("Lever returned no Waabi jobs; the output file was not replaced.")

    seen_job_ids: set[str] = set()
    for position, record in enumerate(records, start=1):
        missing = [field for field in REQUIRED_FIELDS if not record.get(field)]
        if missing:
            fields = ", ".join(missing)
            raise ValueError(f"Waabi job record {position} is missing required fields: {fields}.")

        job_id = str(record["job_id"])
        if job_id in seen_job_ids:
            raise ValueError(f"Lever returned duplicate Waabi job ID: {job_id}.")
        seen_job_ids.add(job_id)


def scrape_waabi_jobs(timeout: float = 30.0) -> list[dict[str, Any]]:
    """Fetch and normalize all currently published Waabi jobs."""

    collected_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    records = [normalize_job(job, collected_at) for job in fetch_jobs(timeout=timeout)]
    validate_records(records)
    return records


def write_json(records: list[dict[str, Any]], output_path: Path) -> None:
    """Write records as UTF-8 JSON, creating the output directory if needed."""

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
        description="Download Waabi's published Lever jobs and save normalized JSON."
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
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        records = scrape_waabi_jobs(timeout=args.timeout)
        write_json(records, args.output)
    except (RuntimeError, ValueError) as exc:
        print(f"Waabi scraper failed: {exc}", file=sys.stderr)
        return 1

    print(f"Saved {len(records)} Waabi jobs to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
