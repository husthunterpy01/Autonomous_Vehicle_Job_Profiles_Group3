from __future__ import annotations

import html
import re
from datetime import UTC, datetime
from html.parser import HTMLParser
from typing import Any, Iterable, Mapping


class _TextExtractor(HTMLParser):
    BLOCK_TAGS = frozenset(
        {
            "address",
            "article",
            "br",
            "div",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "li",
            "p",
            "section",
            "tr",
        }
    )

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


class SilverCleaner:
    """Clean and deduplicate flat Bronze job-posting records.

    AV-domain classification deliberately does not belong here; that work is
    owned by the separate classification task.
    """

    EMPLOYMENT_TYPES = {
        "fulltime": "full-time",
        "full time": "full-time",
        "full-time": "full-time",
        "parttime": "part-time",
        "part time": "part-time",
        "part-time": "part-time",
        "contract": "contract",
        "contractor": "contract",
        "temporary": "temporary",
        "temp": "temporary",
        "intern": "internship",
        "internship": "internship",
    }

    @classmethod
    def clean_records(cls, records: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
        cleaned = [record for item in records if (record := cls.clean_record(item)) is not None]
        selected: dict[tuple[Any, ...], dict[str, Any]] = {}
        order: list[tuple[Any, ...]] = []

        for record in cleaned:
            key = cls.deduplication_key(record)
            if key not in selected:
                selected[key] = record
                order.append(key)
                continue
            if cls._preference(record) > cls._preference(selected[key]):
                selected[key] = record

        return [selected[key] for key in order]

    @classmethod
    def clean_record(cls, raw: Mapping[str, Any]) -> dict[str, Any] | None:
        title = cls.clean_text(raw.get("job_name") or raw.get("job_title") or raw.get("title"))
        if not title:
            return None

        source = cls.clean_text(
            raw.get("ats_name") or raw.get("source_system") or raw.get("source")
        )
        company = cls.clean_text(raw.get("company_name") or raw.get("company"))
        locations = cls.normalize_locations(raw.get("locations") or raw.get("location"))

        return {
            "id": cls.clean_identifier(raw.get("id")),
            "source_job_id": cls.clean_identifier(raw.get("source_job_id") or raw.get("job_id")),
            "ats_name": source,
            "company_name": company,
            "job_name": title,
            "job_description": cls.html_to_text(
                raw.get("job_description")
                or raw.get("description_text")
                or raw.get("description_html")
            ),
            "headquarter": cls.clean_text(raw.get("headquarter")),
            "locations": locations,
            "department": cls.clean_text(raw.get("department")),
            "team": cls.clean_text(raw.get("team")),
            "job_url": cls.clean_text(raw.get("job_url") or raw.get("canonical_job_url")),
            "job_uploaded_at": cls.normalize_datetime(
                raw.get("job_uploaded_at") or raw.get("published_at")
            ),
            "employment_type": cls.normalize_employment_type(raw.get("employment_type")),
            "workplace_type": cls.clean_text(raw.get("workplace_type")),
            "ingested_at": cls.normalize_datetime(
                raw.get("ingested_at") or raw.get("retrieved_at")
            ),
        }

    @staticmethod
    def clean_identifier(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return None if not text or text.lower() in {"nan", "none", "null"} else text

    @staticmethod
    def clean_text(value: Any) -> str | None:
        if value is None:
            return None
        text = html.unescape(str(value)).replace("\u00a0", " ")
        text = re.sub(r"\s+", " ", text).strip()
        return None if not text or text.lower() in {"nan", "none", "null"} else text

    @classmethod
    def html_to_text(cls, value: Any) -> str | None:
        if value is None:
            return None
        decoded = html.unescape(html.unescape(str(value)))
        parser = _TextExtractor()
        parser.feed(decoded)
        parser.close()
        lines = [re.sub(r"\s+", " ", line).strip() for line in "".join(parser.parts).splitlines()]
        text = "\n".join(line for line in lines if line)
        return cls.clean_text(text.replace("\n", " "))

    @classmethod
    def normalize_locations(cls, value: Any) -> tuple[str, ...]:
        if value is None:
            return ()
        values = (
            value
            if isinstance(value, (list, tuple, set))
            else re.split(r"\s*\|\s*", str(value))
        )
        locations: list[str] = []
        seen: set[str] = set()
        for item in values:
            location = cls.clean_text(item)
            if location and location.casefold() not in seen:
                locations.append(location)
                seen.add(location.casefold())
        return tuple(locations)

    @classmethod
    def normalize_employment_type(cls, value: Any) -> str | None:
        cleaned = cls.clean_text(value)
        if not cleaned:
            return None
        key = re.sub(r"\s+", " ", cleaned.casefold()).strip()
        return cls.EMPLOYMENT_TYPES.get(key, key)

    @staticmethod
    def normalize_datetime(value: Any) -> datetime | None:
        if value is None or value == "":
            return None
        try:
            if isinstance(value, datetime):
                parsed = value
            elif isinstance(value, (int, float)) or str(value).strip().isdigit():
                number = float(value)
                if abs(number) >= 100_000_000_000:
                    number /= 1000
                parsed = datetime.fromtimestamp(number, tz=UTC)
            else:
                parsed = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            return parsed.astimezone(UTC)
        except (OverflowError, TypeError, ValueError):
            return None

    @classmethod
    def deduplication_key(cls, record: Mapping[str, Any]) -> tuple[Any, ...]:
        source = cls._normalized_key_part(record.get("ats_name"))
        source_job_id = cls.clean_identifier(record.get("source_job_id"))
        if source_job_id:
            return ("source-job-id", source, source_job_id.casefold())

        url = cls.clean_text(record.get("job_url"))
        if url:
            return ("url", source, url.casefold().rstrip("/"))

        uploaded = record.get("job_uploaded_at")
        uploaded_key = uploaded.isoformat() if isinstance(uploaded, datetime) else ""
        return (
            "fallback",
            cls._normalized_key_part(record.get("company_name")),
            cls._normalized_key_part(record.get("job_name")),
            uploaded_key,
            tuple(sorted(cls._normalized_key_part(item) for item in record.get("locations", ()))),
        )

    @classmethod
    def _normalized_key_part(cls, value: Any) -> str:
        return (cls.clean_text(value) or "").casefold()

    @staticmethod
    def _preference(record: Mapping[str, Any]) -> tuple[int, datetime]:
        completeness = sum(
            value not in (None, "", (), [])
            for key, value in record.items()
            if key not in {"id", "ingested_at"}
        )
        ingested_at = record.get("ingested_at")
        if not isinstance(ingested_at, datetime):
            ingested_at = datetime.min.replace(tzinfo=UTC)
        return completeness, ingested_at
