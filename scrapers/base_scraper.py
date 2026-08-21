"""Shared HTTP, text-cleaning, validation, and output logic for job scrapers."""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from scrapers.bronze_storage import (
    BronzeStorage,
    BronzeStorageError,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
logger = logging.getLogger(__name__)
DEFAULT_USER_AGENT = (
    "AutonomousVehicleJobProfiles/1.0 (academic job-market research)"
)
COMMON_REQUIRED_FIELDS = (
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
    """Preserve useful line breaks while removing HTML tags."""

    BLOCK_TAGS = {
        "br",
        "div",
        "h1",
        "h2",
        "h3",
        "li",
        "ol",
        "p",
        "section",
        "ul",
    }

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        if tag.lower() in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


class BaseJobScraper(ABC):
    """Template method for fetching, normalizing, validating, and saving jobs."""

    company_name: str
    ats_name: str
    output_filename: str
    required_fields: tuple[str, ...] = COMMON_REQUIRED_FIELDS

    def __init__(
        self,
        user_agent: str = DEFAULT_USER_AGENT,
        bronze_storage: BronzeStorage | None = None,
    ) -> None:
        self.user_agent = user_agent
        self.bronze_storage = bronze_storage or BronzeStorage()

    @property
    def default_output(self) -> Path:
        return PROJECT_ROOT / "data" / self.output_filename

    @staticmethod
    def clean_text(value: Any) -> str:
        """Return consistently spaced, entity-decoded plain text."""

        if value is None:
            return ""
        text = unescape(str(value)).replace("\r\n", "\n").replace("\r", "\n")
        lines = [
            re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()
        ]
        return "\n".join(line for line in lines if line)

    @classmethod
    def html_to_text(cls, value: Any) -> str:
        """Decode up to three layers of entities, then remove HTML tags."""

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
        return cls.clean_text("".join(parser.parts))

    @classmethod
    def label(cls, value: Any) -> str:
        """Read a standard ATS object shaped like {label: value}."""

        return cls.clean_text(value.get("label")) if isinstance(value, dict) else ""

    @staticmethod
    def to_utc_iso8601(value: Any, *, epoch_milliseconds: bool = False) -> str:
        """Normalize an ATS timestamp to second-precision UTC ISO 8601."""

        if value is None or isinstance(value, bool):
            return ""

        parsed: datetime
        try:
            if isinstance(value, (int, float)):
                divisor = 1000 if epoch_milliseconds else 1
                parsed = datetime.fromtimestamp(value / divisor, tz=timezone.utc)
            elif isinstance(value, datetime):
                parsed = value
            elif isinstance(value, str):
                text = value.strip()
                if not text:
                    return ""
                if text[-1:].casefold() == "z":
                    text = f"{text[:-1]}+00:00"
                parsed = datetime.fromisoformat(text)
            else:
                return ""
        except (OSError, OverflowError, TypeError, ValueError):
            return ""

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return (
            parsed.astimezone(timezone.utc)
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z")
        )

    def fetch_json(
        self,
        url: str,
        timeout: float = 30.0,
        retries: int = 3,
    ) -> Any:
        """GET JSON with consistent headers and temporary-failure retries."""

        request = Request(
            url,
            headers={"Accept": "application/json", "User-Agent": self.user_agent},
        )

        for attempt in range(1, retries + 1):
            try:
                with urlopen(request, timeout=timeout) as response:  # noqa: S310
                    return json.load(response)
            except HTTPError as exc:
                retryable = exc.code == 429 or 500 <= exc.code < 600
                if not retryable or attempt == retries:
                    raise RuntimeError(
                        f"{self.ats_name} request failed with HTTP {exc.code}: {url}"
                    ) from exc

                retry_after = exc.headers.get("Retry-After")
                try:
                    delay = (
                        float(retry_after)
                        if retry_after
                        else float(2 ** (attempt - 1))
                    )
                except ValueError:
                    delay = float(2 ** (attempt - 1))
                time.sleep(max(delay, 0.0))
            except URLError as exc:
                if attempt == retries:
                    raise RuntimeError(
                        f"Could not connect to {self.ats_name}: {exc.reason}"
                    ) from exc
                time.sleep(2 ** (attempt - 1))

        raise RuntimeError(f"{self.ats_name} request failed after all retries.")

    @abstractmethod
    def fetch_jobs(self, timeout: float = 30.0) -> list[dict[str, Any]]:
        """Return raw public job objects from the company ATS."""

    @abstractmethod
    def normalize_job(
        self, job: dict[str, Any], collected_at: str
    ) -> dict[str, Any]:
        """Map one ATS object into the project's common job schema."""

    @abstractmethod
    def source_url_for_job(self, job: dict[str, Any]) -> str:
        """Read a posting's public source URL from its raw ATS object."""

    def scrape(self, timeout: float = 30.0) -> list[dict[str, Any]]:
        """Execute the shared scraper lifecycle."""

        raw_jobs = self.fetch_jobs(timeout=timeout)
        collected_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        try:
            bronze_paths = self.bronze_storage.persist_jobs(
                raw_jobs,
                source_company=self.company_name,
                source_url_for_job=self.source_url_for_job,
                scrape_timestamp=collected_at,
            )
        except BronzeStorageError as exc:
            raise RuntimeError(
                f"Bronze persistence failed for {self.company_name}."
            ) from exc

        logger.info(
            "Bronze persistence completed company=%s records=%d "
            "scrape_timestamp=%s",
            self.company_name,
            len(bronze_paths),
            collected_at,
        )
        records = [self.normalize_job(job, collected_at) for job in raw_jobs]
        self.validate_records(records)
        return records

    def validate_records(self, records: list[dict[str, Any]]) -> None:
        """Reject empty, incomplete, or duplicate output before it is saved."""

        if not records:
            raise ValueError(f"{self.ats_name} returned no {self.company_name} jobs.")

        seen_job_ids: set[str] = set()
        for position, record in enumerate(records, start=1):
            missing = [field for field in self.required_fields if not record.get(field)]
            if missing:
                fields = ", ".join(missing)
                raise ValueError(
                    f"{self.company_name} job record {position} is missing: {fields}."
                )

            job_id = str(record["job_id"])
            if job_id in seen_job_ids:
                raise ValueError(
                    f"{self.ats_name} returned duplicate {self.company_name} "
                    f"job ID: {job_id}."
                )
            seen_job_ids.add(job_id)

    @staticmethod
    def write_json(records: list[dict[str, Any]], output_path: Path) -> None:
        """Write UTF-8 JSON atomically so failed runs keep previous output."""

        output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = output_path.with_suffix(output_path.suffix + ".tmp")
        try:
            with temporary_path.open("w", encoding="utf-8", newline="\n") as file:
                json.dump(records, file, ensure_ascii=False, indent=2)
                file.write("\n")
            temporary_path.replace(output_path)
        finally:
            temporary_path.unlink(missing_ok=True)

    def execute(self, output_path: Path, timeout: float = 30.0) -> int:
        """Run one scraper and provide a consistent command-line result."""

        configure_scraper_logging()
        try:
            records = self.scrape(timeout=timeout)
            self.write_json(records, output_path)
        except (RuntimeError, ValueError) as exc:
            logger.exception(
                "Scraper failed company=%s output_path=%s",
                self.company_name,
                output_path,
            )
            print(f"{self.company_name} scraper failed: {exc}", file=sys.stderr)
            return 1

        print(f"Saved {len(records)} {self.company_name} jobs to {output_path}")
        return 0


def configure_scraper_logging() -> None:
    """Provide concise standard logging for standalone scraper commands."""

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def build_common_parser(description: str, default_output: Path) -> argparse.ArgumentParser:
    """Create the CLI arguments shared by every company scraper."""

    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--output",
        type=Path,
        default=default_output,
        help=f"JSON output path (default: {default_output})",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="HTTP timeout in seconds (default: 30)",
    )
    return parser


def validate_common_args(
    parser: argparse.ArgumentParser, args: argparse.Namespace
) -> argparse.Namespace:
    """Apply shared command-line validation."""

    if args.timeout <= 0:
        parser.error("--timeout must be greater than 0")
    return args
