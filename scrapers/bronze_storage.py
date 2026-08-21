"""Append-only persistence for raw job objects in the Bronze data layer."""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
from collections.abc import Callable, Sequence
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BRONZE_ROOT = PROJECT_ROOT / "data" / "bronze"
UTC_TIMESTAMP_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
    r"(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$"
)

logger = logging.getLogger(__name__)


class BronzeStorageError(RuntimeError):
    """Raised when a raw job object cannot be persisted safely."""


class BronzeStorage:
    """Store each raw job object as a new, immutable JSON record."""

    def __init__(self, root: Path = DEFAULT_BRONZE_ROOT) -> None:
        self.root = root

    def persist_jobs(
        self,
        jobs: Sequence[dict[str, Any]],
        *,
        source_company: str,
        source_url_for_job: Callable[[dict[str, Any]], str],
        scrape_timestamp: str | None = None,
    ) -> list[Path]:
        """Persist raw jobs without modifying, cleaning, or deduplicating them."""

        timestamp_value = (
            scrape_timestamp if scrape_timestamp is not None else self._utc_now()
        )
        try:
            parsed_timestamp = self._parse_utc_timestamp(timestamp_value)
            timestamp = self._format_utc_timestamp(parsed_timestamp)
            company_slug = self._company_slug(source_company)
        except (TypeError, ValueError) as exc:
            logger.exception(
                "Invalid Bronze record metadata company=%s scrape_timestamp=%r",
                source_company,
                timestamp_value,
            )
            raise BronzeStorageError(
                "Bronze records require a valid UTC ISO-8601 scrape timestamp."
            ) from exc

        date_partition = parsed_timestamp.strftime("%Y-%m-%d")
        filename_timestamp = parsed_timestamp.strftime("%Y%m%dT%H%M%S.%fZ")
        written_paths: list[Path] = []

        for job in jobs:
            record_id = str(uuid4())
            output_path = (
                self.root
                / company_slug
                / date_partition
                / f"{filename_timestamp}_{record_id}.json"
            )
            source_url = ""

            try:
                source_url = source_url_for_job(job)
                if not isinstance(source_url, str) or not source_url:
                    raise ValueError("raw job object does not contain a source URL")
                record = {
                    "record_id": record_id,
                    "source_company": source_company,
                    "source_url": source_url,
                    "scrape_timestamp": timestamp,
                    "raw_payload": job,
                }
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path = self._safe_output_path(output_path)
                self._write_exclusive_json(output_path, record)
            except (OSError, TypeError, ValueError) as exc:
                logger.exception(
                    "Bronze persistence failed company=%s source_url=%s "
                    "record_id=%s output_path=%s persisted_records=%d "
                    "total_records=%d",
                    source_company,
                    source_url,
                    record_id,
                    output_path,
                    len(written_paths),
                    len(jobs),
                )
                raise BronzeStorageError(
                    f"Could not persist Bronze record for {source_company}: {source_url}"
                ) from exc

            written_paths.append(output_path)

        return written_paths

    @staticmethod
    def _write_exclusive_json(output_path: Path, record: dict[str, Any]) -> None:
        """Atomically publish one complete record without replacing another."""

        file_descriptor = -1
        temporary_path: Path | None = None
        try:
            file_descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{output_path.stem}.",
                suffix=".tmp",
                dir=output_path.parent,
            )
            temporary_path = Path(temporary_name)
            temporary_file = os.fdopen(
                file_descriptor,
                mode="w",
                encoding="utf-8",
                newline="\n",
            )
            file_descriptor = -1
            with temporary_file as file:
                json.dump(record, file, ensure_ascii=False, indent=2)
                file.write("\n")
                file.flush()
                os.fsync(file.fileno())

            os.link(temporary_path, output_path)
        finally:
            try:
                if file_descriptor >= 0:
                    os.close(file_descriptor)
            finally:
                if temporary_path is not None:
                    temporary_path.unlink(missing_ok=True)

    def _safe_output_path(self, output_path: Path) -> Path:
        """Resolve a record path and reject anything outside the Bronze root."""

        resolved_root = self.root.resolve(strict=True)
        resolved_parent = output_path.parent.resolve(strict=True)
        resolved_output = resolved_parent / output_path.name
        try:
            resolved_output.relative_to(resolved_root)
        except ValueError as exc:
            raise ValueError(
                f"Bronze output path escapes storage root: {resolved_output}"
            ) from exc
        return resolved_output

    @staticmethod
    def _company_slug(company: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", company.casefold()).strip("-")
        if not slug:
            raise ValueError("source company must produce a non-empty directory name")
        return slug

    @staticmethod
    def _parse_utc_timestamp(timestamp: str) -> datetime:
        if not isinstance(timestamp, str) or not UTC_TIMESTAMP_PATTERN.fullmatch(
            timestamp
        ):
            raise ValueError("scrape timestamp is not valid ISO-8601")

        iso_timestamp = (
            f"{timestamp[:-1]}+00:00" if timestamp.endswith("Z") else timestamp
        )
        parsed = datetime.fromisoformat(iso_timestamp)
        if parsed.utcoffset() != timedelta(0):
            raise ValueError("scrape timestamp must represent UTC")
        return parsed.astimezone(timezone.utc)

    @staticmethod
    def _format_utc_timestamp(timestamp: datetime) -> str:
        """Return the canonical UTC timestamp stored in Bronze metadata."""

        return timestamp.isoformat(timespec="microseconds").replace("+00:00", "Z")

    @staticmethod
    def _utc_now() -> str:
        return (
            datetime.now(timezone.utc)
            .isoformat(timespec="microseconds")
            .replace("+00:00", "Z")
        )
