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
WORKDAY_ATS = "workday"
DETAIL_PAUSE_SECONDS = 0.1

logger = logging.getLogger(__name__)


class RawFetch:
    """Fetch a career URL (API JSON or HTML) and store the raw body in MinIO."""
    def __init__(
        self,
        company_name: str,
        source: str,
        source_system: str,
        fallback_urls: list[str] | None = None,
        request_method: str = "GET",
        request_body: bytes | None = None,
    ) -> None:
        self.company_name = company_name
        self.source = source
        self.source_system = source_system
        self.fallback_urls = fallback_urls or []
        self.request_method = request_method.upper()
        self.request_body = request_body

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

        source_config = sources[ats_name]

        slug = company.get("slug")
        url_context: dict[str, Any] = dict(company.get("params") or {})
        if isinstance(slug, str) and slug:
            url_context["slug"] = slug
        try:
            job_url = source_config["api_base"].format(**url_context)
            fallback_urls = [
                template.format(**url_context)
                for key, template in sorted(source_config.items())
                if key != "api_base" and key.startswith("api_base")
            ]
        except KeyError as exc:
            raise ValueError(
                f"{company_name} is missing URL parameter {exc} for {ats_name}"
            ) from exc

        request_method = str(source_config.get("method", "GET")).upper()
        raw_body = source_config.get("body")
        request_body = raw_body.encode("utf-8") if isinstance(raw_body, str) else None

        return (
            RawFetch(
                company_name,
                "api",
                ats_name,
                fallback_urls,
                request_method=request_method,
                request_body=request_body,
            ),
            job_url,
        )

    def fetch_and_archive(self, url: str, timeout: float = 30.0) -> str:
        candidates = [url, *self.fallback_urls]
        last_error = RuntimeError(f"{self.source_system} had no URL to fetch")
        for index, candidate in enumerate(candidates):
            try:
                return self._fetch_and_archive_one(candidate, timeout=timeout)
            except RuntimeError as exc:
                last_error = exc
                if index + 1 < len(candidates):
                    logger.warning(
                        "%s fetch failed for %s (%s); trying fallback URL %s",
                        self.source_system,
                        candidate,
                        exc,
                        candidates[index + 1],
                    )
        raise last_error

    def _fetch_and_archive_one(self, url: str, timeout: float = 30.0) -> str:
        body, status, content_type = self._http_get(
            url,
            timeout=timeout,
            method=self.request_method,
            data=self.request_body,
        )
        if self.source_system in SMARTRECRUITERS_ATS:
            body = self._expand_smartrecruiters_postings(url, body, timeout=timeout)
        elif self.source_system == WORKDAY_ATS:
            body = self._expand_workday_postings(url, body, timeout=timeout)
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

    def _expand_workday_postings(
        self, list_url: str, body: bytes, timeout: float
    ) -> dict[str, Any] | bytes:
        """Page the Workday list endpoint, then attach each job's detail payload.

        The ``/jobs`` list endpoint (POST) only returns summary fields; the full
        ``jobDescription`` HTML lives on the per-job detail endpoint (GET) at the
        CXS base plus the posting's ``externalPath``.
        """
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return body
        if not isinstance(payload, dict):
            return body
        postings = payload.get("jobPostings")
        if not isinstance(postings, list):
            return payload

        total = payload.get("total")
        if isinstance(total, int):
            postings = self._collect_workday_pages(list_url, postings, total, timeout)

        detail_root = self._workday_detail_root(list_url)
        for posting in postings:
            external_path = (
                posting.get("externalPath") if isinstance(posting, dict) else None
            )
            if not external_path:
                continue
            detail_url = f"{detail_root}{external_path}"
            try:
                detail_body, _, _ = self._http_get(detail_url, timeout=timeout)
                detail = json.loads(detail_body)
            except (RuntimeError, json.JSONDecodeError) as exc:
                logger.warning("Workday detail failed for %s: %s", external_path, exc)
                continue
            if isinstance(detail, dict):
                posting["jobPostingDetail"] = detail
            time.sleep(DETAIL_PAUSE_SECONDS)

        payload["jobPostings"] = postings
        return payload

    def _collect_workday_pages(
        self, list_url: str, postings: list[Any], total: int, timeout: float
    ) -> list[Any]:
        """Follow Workday's offset/limit paging so every summary posting is kept."""
        try:
            page_request = json.loads(self.request_body) if self.request_body else {}
        except (json.JSONDecodeError, TypeError):
            page_request = {}
        if not isinstance(page_request, dict):
            page_request = {}

        offset = len(postings)
        while 0 < offset < total:
            page_request["offset"] = offset
            try:
                page_body, _, _ = self._http_get(
                    list_url,
                    timeout=timeout,
                    method="POST",
                    data=json.dumps(page_request).encode("utf-8"),
                )
                page = json.loads(page_body)
            except (RuntimeError, json.JSONDecodeError) as exc:
                logger.warning("Workday page at offset %s failed: %s", offset, exc)
                break
            page_postings = page.get("jobPostings") if isinstance(page, dict) else None
            if not isinstance(page_postings, list) or not page_postings:
                break
            postings.extend(page_postings)
            offset += len(page_postings)
            time.sleep(DETAIL_PAUSE_SECONDS)
        return postings

    @staticmethod
    def _workday_detail_root(list_url: str) -> str:
        parts = urlsplit(list_url)
        path = parts.path
        if path.endswith("/jobs"):
            path = path[: -len("/jobs")]
        else:
            path = path.rsplit("/", 1)[0]
        return urlunsplit((parts.scheme, parts.netloc, path, "", ""))

    def _http_get(
        self,
        url: str,
        timeout: float = 30.0,
        no_retries: int = 3,
        method: str = "GET",
        data: bytes | None = None,
    ) -> tuple[bytes, int, str]:
        headers = {
            "Accept": "application/json, text/html;q=0.9, */*;q=0.8",
            "User-Agent": USER_AGENT,
        }
        if data is not None:
            headers["Content-Type"] = "application/json"
        job_request = Request(url, data=data, method=method, headers=headers)
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
