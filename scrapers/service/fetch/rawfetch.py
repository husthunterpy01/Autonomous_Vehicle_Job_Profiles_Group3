from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

import yaml

from scrapers.config.minio import MinioConfig
from scrapers.response_archive import ResponseArchive

ATS_PATH = "./scrapers/data/ats_sources.yaml"
USER_AGENT = "Mozilla/5.0"
SMARTRECRUITERS_ATS = frozenset({"smartrecruiters", "smartrecruiter"})
DETAIL_PAUSE_SECONDS = 0.1

logger = logging.getLogger(__name__)


class RawFetch:
    """Fetch a career URL (API JSON or HTML) and store the raw body in MinIO."""
    def __init__(self, company_name: str, source: str, source_system: str) -> None:
        self.company_name = company_name
        self.source = source
        self.source_system = source_system

    @classmethod
    def from_company(cls, company: dict[str, Any], ats_path: str | None = None) -> tuple[RawFetch, str]:
        ats_name = company["ats"]
        company_name = company["name"]
        if ats_name == "html":
            page_url = company.get("url")
            if not isinstance(page_url, str) or not page_url:
                raise ValueError(f"{company_name} is missing a career page URL")
            return RawFetch(company_name, "html", ats_name), page_url

        config_path = ats_path or ATS_PATH
        with open(config_path, encoding="utf-8") as file:
            ats_config = yaml.safe_load(file) or {}
        sources = ats_config.get("ats_sources") or {}
        if ats_name not in sources:
            raise ValueError(f"ATS name is not available in the ATS list: {ats_name}")

        slug = company.get("slug")
        if not isinstance(slug, str) or not slug:
            raise ValueError(f"{company_name} is missing a slug")
        job_url = sources[ats_name]["api_base"].format(slug=slug)
        return RawFetch(company_name, "api", ats_name), job_url

    def fetch_and_archive(self, url: str, timeout: float = 30.0) -> str:
        body, status, content_type = self._http_get(url, timeout=timeout)
        if self.source_system in SMARTRECRUITERS_ATS:
            body = self._expand_smartrecruiters_postings(url, body, timeout=timeout)
        archive = ResponseArchive(MinioConfig())
        return archive.save_raw_response(
            company_name=self.company_name,
            collected_at=datetime.now(timezone.utc),
            raw_response=body,
            source=self.source,
            source_system=self.source_system,
            url=url,
            status=status,
            content_type=content_type,
        )

    def _expand_smartrecruiters_postings(self, list_url: str, body: bytes, timeout: float) -> dict[str, Any] | bytes:
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return body
        postings = payload.get("content") if isinstance(payload, dict) else None
        if not isinstance(postings, list):
            return payload if isinstance(payload, dict) else body

        detail_root = self._smartrecruiters_detail_root(list_url)
        expanded: list[Any] = []
        for posting in postings:
            posting_id = posting.get("id") if isinstance(posting, dict) else None
            if not posting_id:
                expanded.append(posting)
                continue
            detail_url = f"{detail_root}/{posting_id}"
            try:
                detail_body, _, _ = self._http_get(detail_url, timeout=timeout)
                detail = json.loads(detail_body)
                expanded.append(detail if isinstance(detail, dict) else posting)
            except (RuntimeError, json.JSONDecodeError) as exc:
                logger.warning("SmartRecruiters detail failed for %s: %s", posting_id, exc)
                expanded.append(posting)
            time.sleep(DETAIL_PAUSE_SECONDS)
        payload["content"] = expanded
        return payload

    @staticmethod
    def _smartrecruiters_detail_root(list_url: str) -> str:
        parts = urlsplit(list_url)
        return urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip("/"), "", ""))

    def _http_get(self, url: str, timeout: float = 30.0, no_retries: int = 3) -> tuple[bytes, int, str]:
        job_request = Request(
            url,
            headers={
                "Accept": "application/json, text/html;q=0.9, */*;q=0.8",
                "User-Agent": USER_AGENT,
            },
        )
        for attempt in range(1, no_retries + 1):
            try:
                with urlopen(job_request, timeout=timeout) as response:
                    body = response.read()
                    status = getattr(response, "status", None) or response.getcode()
                    content_type = response.headers.get("Content-Type") or ""
                    return body, int(status), content_type
            except HTTPError as exc:
                retryable = exc.code == 429 or 500 <= exc.code < 600
                if not retryable or attempt == no_retries:
                    raise RuntimeError(
                        f"{self.source_system} request failed with HTTP {exc.code}: {url}"
                    ) from exc
                retry_after = exc.headers.get("Retry-After") if exc.headers is not None else None
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
                if attempt == no_retries:
                    raise RuntimeError(
                        f"Could not connect to {self.source_system}: {exc.reason}"
                    ) from exc
                time.sleep(2 ** (attempt - 1))

        raise RuntimeError(f"{self.source_system} request failed after all retries.")
