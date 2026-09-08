from __future__ import annotations

import json
import logging
import re
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Selector-driven fields lifted straight out of each job row. Keys match the
# column names the bronze models select, so the html_jobs dbt model is a
# straight passthrough. ``job_name`` / ``job_url`` are handled separately.
ROW_FIELDS = ("job_description", "location", "employment_type", "job_uploaded_at")

# Jobylon embeds the whole job list as a JS array literal assigned to
# ``JBL.embed_v2['jobs']`` inside the widget HTML.
JOBYLON_ARRAY_RE = re.compile(r"JBL\.embed_v2\['jobs'\]\s*=\s*(\[.*?\]);", re.DOTALL)
JOBYLON_JOB_BASE = "https://emp.jobylon.com"


class HTMLExtractor:
    """Parse a fetched career page into bronze-ready job dicts.

    ``config`` is the company's entry from ``ats_sources.yaml`` -> ``html_sources``.
    ``page_url`` is the URL the HTML was fetched from; relative job links are
    resolved against it. ``ats_name`` / ``company_name`` / ``headquarter`` are
    not produced here -- they come from the ``bronze.raw_responses`` row.
    """

    def __init__(
        self,
        html_content: str | bytes,
        config: dict[str, Any] | None,
        page_url: str | None = None,
    ) -> None:
        self.html_content = html_content
        self.config = config or {}
        self.page_url = page_url

    def extract_jobs(self) -> list[dict[str, Any]]:
        strategy = self.config.get("strategy", "css_list")
        handler = getattr(self, f"_strategy_{strategy}", None)
        if handler is None:
            logger.error("Unknown HTML strategy %r for %s", strategy, self.page_url)
            return []
        return handler()

    def _strategy_headless(self) -> list[dict[str, Any]]:
        """Placeholder: the page renders its jobs client-side and needs a browser."""
        logger.warning(
            "HTML source %s uses the 'headless' strategy; skipped until a "
            "browser-backed strategy or CSS selectors are added.",
            self.page_url,
        )
        return []

    def _strategy_css_list(self) -> list[dict[str, Any]]:
        item_selector = self.config.get("item")
        if not item_selector:
            logger.error("css_list strategy for %s is missing 'item'", self.page_url)
            return []

        soup = BeautifulSoup(self._as_text(self.html_content), "html.parser")
        link_selector = self.config.get("link", "a")
        id_pattern = self.config.get("job_id_pattern")
        details = self._detail_map(soup)

        jobs: list[dict[str, Any]] = []
        seen: set[str] = set()
        for row in soup.select(item_selector):
            job_url = self._resolve_link(row, link_selector)
            job = {
                "source_job_id": self._job_id(job_url, id_pattern),
                "job_name": self._text(row, self.config.get("job_name")),
                "job_url": job_url,
            }
            for field in ROW_FIELDS:
                job[field] = self._text(row, self.config.get(field))
            if not job["job_description"] and details:
                job["job_description"] = details.get(job["source_job_id"]) or details.get(job_url)
            if not (job["job_name"] or job["job_url"]):
                continue
            # Paginated fetches concatenate page snapshots; drop repeats.
            dedupe_key = str(job["source_job_id"] or job["job_url"] or job["job_name"])
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            jobs.append(job)

        if not jobs:
            logger.warning("css_list strategy for %s matched no jobs", self.page_url)
        return jobs

    def _strategy_jobylon(self) -> list[dict[str, Any]]:
        """Parse the ``JBL.embed_v2['jobs']`` JS array from a Jobylon widget page."""
        text = self._as_text(self.html_content)
        match = JOBYLON_ARRAY_RE.search(text)
        if not match:
            logger.warning("jobylon strategy for %s found no jobs array", self.page_url)
            return []

        details = self._detail_map(BeautifulSoup(text, "html.parser"))
        jobs: list[dict[str, Any]] = []
        for blob in self._split_js_objects(match.group(1)):
            job_id = self._js_field(blob, "id")
            path = self._js_field(blob, "url")
            jobs.append(
                {
                    "source_job_id": job_id,
                    "job_name": self._js_field(blob, "title"),
                    "job_description": details.get(job_id),
                    "location": self._js_field(blob, "locations_text"),
                    "employment_type": self._js_list_first(blob, "layers_1"),
                    "job_uploaded_at": None,
                    "job_url": f"{JOBYLON_JOB_BASE}{path}" if path else None,
                }
            )
        return [job for job in jobs if job["source_job_id"] or job["job_name"]]

    @staticmethod
    def _split_js_objects(array_blob: str) -> list[str]:
        """Yield each top-level ``{...}`` chunk of a JS array literal."""
        chunks: list[str] = []
        depth = 0
        start = None
        for index, char in enumerate(array_blob):
            if char == "{":
                if depth == 0:
                    start = index
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0 and start is not None:
                    chunks.append(array_blob[start : index + 1])
                    start = None
        return chunks

    @classmethod
    def _js_field(cls, blob: str, key: str) -> str | None:
        match = re.search(rf"\b{key}:\s*'((?:[^'\\]|\\.)*)'", blob)
        return cls._unescape_js(match.group(1)) if match else None

    @classmethod
    def _js_list_first(cls, blob: str, key: str) -> str | None:
        match = re.search(rf"'{key}':\s*\[\s*'((?:[^'\\]|\\.)*)'", blob)
        return cls._unescape_js(match.group(1)) if match else None

    @staticmethod
    def _unescape_js(value: str) -> str | None:
        value = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), value)
        value = value.replace("\\/", "/").replace("\\'", "'").replace('\\"', '"')
        return value.strip() or None

    @staticmethod
    def _detail_map(soup: Any) -> dict[str, str]:
        """Descriptions RawFetch fetched from per-job pages, keyed by id or URL."""
        tag = soup.select_one('script[type="application/x-bronze-detail"]')
        if tag is None or not tag.string:
            return {}
        try:
            data = json.loads(tag.string)
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}

    def _resolve_link(self, row: Any, link_selector: str) -> str | None:
        anchor = row.select_one(link_selector)
        href = anchor.get("href") if anchor else None
        if not href:
            return None
        return urljoin(self.page_url, href) if self.page_url else href

    @staticmethod
    def _job_id(job_url: str | None, id_pattern: str | None) -> str | None:
        if not job_url:
            return None
        if id_pattern:
            match = re.search(id_pattern, job_url)
            if match:
                return match.group(1)
        return job_url

    @staticmethod
    def _text(row: Any, selector: str | None) -> str | None:
        """Return text for ``selector``; ``"sel@attr"`` returns that attribute."""
        if not selector:
            return None
        selector, _, attr = selector.partition("@")
        node = row.select_one(selector.strip())
        if node is None:
            return None
        if attr:
            value = node.get(attr.strip())
            return value.strip() if isinstance(value, str) and value.strip() else None
        return node.get_text(" ", strip=True) or None

    @staticmethod
    def _as_text(content: str | bytes) -> str:
        if isinstance(content, bytes):
            return content.decode("utf-8", errors="replace")
        return content
