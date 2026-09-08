from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlsplit, urlunsplit
from xml.etree import ElementTree as ET

logger = logging.getLogger(__name__)

POSITION_TAG = "position"

class XMLExtractor:
    """Parse a Personio ``workzag-jobs`` XML feed into bronze-ready job dicts.

    Only the fields the Postgres bronze layer (``bronze.job_postings`` via the
    per-ATS models) consumes are pulled out; the keys match the column names
    those models select so the ``personio`` dbt model is a straight passthrough.
    ``ats_name``/``company_name``/``headquarter`` are not here -- they come from
    the ``bronze.raw_responses`` row, not the feed body.
    """

    def __init__(self, xml_content: str | bytes, feed_url: str | None = None) -> None:
        self.xml_content = xml_content
        self.feed_url = feed_url

    def extract_jobs(self) -> list[dict[str, Any]]:
        """Return one dict per ``<position>``; empty list if the feed is unusable."""
        try:
            root = ET.fromstring(self._as_bytes(self.xml_content))
        except ET.ParseError as exc:
            logger.error("Could not parse Personio XML feed: %s", exc)
            return []

        jobs = [self._position_to_job(position) for position in root.iter(POSITION_TAG)]
        return [job for job in jobs if job["source_job_id"] or job["job_name"]]

    def _position_to_job(self, position: ET.Element) -> dict[str, Any]:
        job_id = self._text(position.find("id"))
        return {
            "source_job_id": job_id,
            "job_name": self._text(position.find("name")),
            "job_description": self._job_description(position),
            "location": self._text(position.find("office")),
            "job_url": self._job_url(job_id),
            "job_uploaded_at": self._text(position.find("createdAt")),
            "employment_type": self._text(position.find("employmentType")),
        }

    def _job_url(self, job_id: str | None) -> str | None:
        """Personio has no per-job URL in the feed; rebuild it from the feed host."""
        if not job_id or not self.feed_url:
            return None
        parts = urlsplit(self.feed_url)
        if not parts.scheme or not parts.netloc:
            return None
        return urlunsplit((parts.scheme, parts.netloc, f"/job/{job_id}", "", ""))

    @staticmethod
    def _job_description(position: ET.Element) -> str | None:
        """Join every ``<jobDescription>`` section into one HTML blob.

        Each section has a ``<name>`` heading and a ``<value>`` CDATA body; the
        parser exposes the CDATA as the element's plain text.
        """
        sections: list[str] = []
        for description in position.findall("./jobDescriptions/jobDescription"):
            heading = XMLExtractor._text(description.find("name"))
            body = XMLExtractor._text(description.find("value"))
            if heading and body:
                sections.append(f"<h3>{heading}</h3>\n{body}")
            elif body or heading:
                sections.append(body or heading)  # type: ignore[arg-type]
        return "\n".join(sections) or None

    @staticmethod
    def _text(element: ET.Element | None) -> str | None:
        if element is None or element.text is None:
            return None
        return element.text.strip() or None

    @staticmethod
    def _as_bytes(content: str | bytes) -> bytes:
        return content if isinstance(content, bytes) else content.encode("utf-8")
