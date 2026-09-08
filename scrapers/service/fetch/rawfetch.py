from __future__ import annotations

import json
import logging
import os
import random
import re
import time
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen

import yaml
from dotenv import load_dotenv

from scrapers.config.minio import MinioConfig
from scrapers.response_archive import ResponseArchive

load_dotenv()
load_dotenv("./scrapers/.env")

ATS_PATH = "./scrapers/data/ats_sources.yaml"
# A real browser UA: Workday/Akamai bot-defence 403s obvious non-browser traffic
# (e.g. "python-requests/2.x" or a bare "Mozilla/5.0") on individual job pages.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36"
)
SMARTRECRUITERS_ATS = frozenset({"smartrecruiters", "smartrecruiter"})
WORKDAY_ATS = "workday"
# Randomised gap between per-job detail calls so bursts of hundreds of requests
# do not trip Workday's rate/burst detection.
DETAIL_PAUSE_RANGE = (0.5, 1.5)
# HTTP codes worth retrying with back-off: rate limiting, transient soft-blocks
# (Workday CXS often answers a soft-block with 403), and 5xx.
RETRYABLE_STATUS = frozenset({403, 429})

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
        render: bool = False,
        wait_for: str | None = None,
        scroll: bool = False,
        paginate: dict[str, Any] | None = None,
        list_config: dict[str, Any] | None = None,
        detail: dict[str, Any] | None = None,
    ) -> None:
        self.company_name = company_name
        self.source = source
        self.source_system = source_system
        self.fallback_urls = fallback_urls or []
        self.request_method = request_method.upper()
        self.request_body = request_body
        self.render = render
        self.wait_for = wait_for
        self.scroll = scroll
        self.paginate = paginate or {}
        # css_list selectors + per-job "detail" page config, for HTML sources
        # whose list page has no job description.
        self.list_config = list_config or {}
        self.detail = detail or {}
        self.list_strategy = (list_config or {}).get("strategy")

    @classmethod
    def from_company(cls, company: dict[str, Any], ats_path: str | None = None) -> tuple[RawFetch, str]:
        ats_name = company["ats"]
        company_name = company["name"]
        config_path = ats_path or ATS_PATH
        if ats_name == "xml":
            feed_url = company.get("url")
            if not isinstance(feed_url, str) or not feed_url:
                raise ValueError(f"{company_name} is missing an XML feed URL")
            # source_system drives the bronze parser (personio's workzag-jobs feed
            # is the only XML format supported today); override via params.format.
            xml_format = str((company.get("params") or {}).get("format", "personio"))
            return RawFetch(company_name, "xml", xml_format), feed_url

        if ats_name == "html":
            html_cfg = cls._load_html_source(company.get("key"), config_path)
            page_url = html_cfg.get("url") or company.get("url")
            if not isinstance(page_url, str) or not page_url:
                raise ValueError(f"{company_name} is missing a career page URL")
            return (
                RawFetch(
                    company_name,
                    "html",
                    ats_name,
                    render=bool(html_cfg.get("render")),
                    wait_for=html_cfg.get("wait_for"),
                    scroll=bool(html_cfg.get("scroll")),
                    paginate=html_cfg.get("paginate"),
                    list_config={
                        key: html_cfg.get(key)
                        for key in ("strategy", "item", "link", "job_id_pattern")
                    },
                    detail=html_cfg.get("detail"),
                ),
                page_url,
            )

        with open(config_path, encoding="utf-8") as file:
            ats_config = yaml.safe_load(file) or {}
        sources = ats_config.get("ats_sources") or {}
        if ats_name not in sources:
            raise ValueError(f"ATS name is not available in the ATS list: {ats_name}")

        source_config = sources[ats_name]

        slug = company.get("slug")
        url_context: dict[str, Any] = cls._resolve_params(company.get("params"), company_name)
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

    @staticmethod
    def _resolve_params(params: dict[str, Any] | None, company_name: str) -> dict[str, Any]:
        """Copy a company's ``params``, expanding ``${VAR}`` from the environment.

        Secrets (e.g. the Comeet API token) live in ``$COMEET_TOKEN`` in the
        environment / CI secrets, never in ``list_companies.yaml``.
        """
        resolved: dict[str, Any] = {}
        for key, value in (params or {}).items():
            if isinstance(value, str) and "$" in value:
                expanded = os.path.expandvars(value)
                if "$" in expanded:
                    raise ValueError(
                        f"{company_name}: unset environment variable for params.{key} "
                        f"({value!r})"
                    )
                resolved[key] = expanded
            else:
                resolved[key] = value
        return resolved

    @staticmethod
    def _load_html_source(company_key: Any, config_path: str) -> dict[str, Any]:
        """Return the ``html_sources`` entry for ``company_key`` (or ``{}``)."""
        if not company_key:
            return {}
        try:
            with open(config_path, encoding="utf-8") as file:
                ats_config = yaml.safe_load(file) or {}
        except OSError:
            return {}
        entry = (ats_config.get("html_sources") or {}).get(company_key)
        return entry if isinstance(entry, dict) else {}

    def _render_html(self, url: str, timeout: float) -> str:
        """Fetch a JS-rendered page's HTML through headless Chrome."""
        try:
            from scrapers.config.selenium_driver import SeleniumClient
        except ImportError as exc:
            raise RuntimeError(
                f"headless rendering for {url} needs the 'selenium' package: {exc}"
            ) from exc
        try:
            with SeleniumClient(page_load_timeout=int(timeout)) as client:
                return client.render(
                    url,
                    wait_selector=self.wait_for,
                    scroll=self.scroll,
                    next_selector=self.paginate.get("next_selector"),
                    max_pages=int(self.paginate.get("max_pages", 1)),
                )
        except Exception as exc:  # noqa: BLE001 - surface any webdriver failure uniformly
            raise RuntimeError(f"headless render failed for {url}: {exc}") from exc

    def _fetch_paginated(self, url: str, timeout: float) -> str:
        """Fetch ``?<param>=<n>`` pages of a static list endpoint and join them.

        Stops at ``max_pages`` or the first near-empty response (the widget's
        way of signalling "no more results").
        """
        param = self.paginate["param"]
        step = int(self.paginate.get("step", 10))
        max_pages = int(self.paginate.get("max_pages", 20))
        separator = "&" if "?" in url else "?"
        pages: list[str] = []
        for page in range(max_pages):
            page_url = f"{url}{separator}{param}={page * step}"
            body, _, _ = self._http_get(page_url, timeout=timeout)
            text = body.decode("utf-8", errors="replace") if isinstance(body, bytes) else str(body)
            if len(text.strip()) < 50:
                break
            pages.append(text)
        return "\n".join(pages)

    def _attach_html_details(self, list_html: Any, base_url: str, timeout: float) -> str:
        """Fetch each job's detail page and embed its description in the list HTML.

        Job rows on some career sites carry no description; it lives on the
        per-job page. We fetch those pages here (at scrape time, so bronze stays
        offline) and append a ``<script type="application/x-bronze-detail">`` map
        of ``{job key: description HTML}`` that HTMLExtractor reads back.
        """
        from bs4 import BeautifulSoup

        text = list_html.decode("utf-8", errors="replace") if isinstance(list_html, bytes) else str(list_html)
        item_selector = self.list_config.get("item")
        if not item_selector:
            return text
        link_selector = self.list_config.get("link") or "a"
        id_pattern = self.list_config.get("job_id_pattern")
        description_selector = self.detail["description"]
        url_template = self.detail.get("url")

        soup = BeautifulSoup(text, "html.parser")
        details: dict[str, str] = {}
        for row in soup.select(item_selector):
            anchor = row.select_one(link_selector)
            href = anchor.get("href") if anchor else None
            if not href:
                continue
            job_url = urljoin(base_url, href)
            job_id = None
            if id_pattern:
                match = re.search(id_pattern, job_url)
                job_id = match.group(1) if match else None
            key = job_id or job_url
            if key in details:
                continue
            detail_url = url_template.format(id=job_id) if (url_template and job_id) else job_url
            try:
                detail_body, _, _ = self._http_get(detail_url, timeout=timeout)
                detail_soup = BeautifulSoup(
                    detail_body.decode("utf-8", errors="replace")
                    if isinstance(detail_body, bytes)
                    else str(detail_body),
                    "html.parser",
                )
                blocks = [
                    node.decode_contents().strip()
                    for node in detail_soup.select(description_selector)
                    if node.get_text(strip=True)
                ]
                if blocks:
                    details[key] = "\n".join(blocks)
            except RuntimeError as exc:
                logger.warning("HTML detail failed for %s: %s", detail_url, exc)
            self._pause_between_details()

        return self._append_detail_script(soup, details)

    def _attach_jobylon_details(self, list_html: Any, timeout: float) -> str:
        """Pull each Jobylon job's description from its page's JobPosting JSON-LD.

        The embed's JS array has no description; the per-job page does, in a
        schema.org ``JobPosting`` blob.
        """
        from bs4 import BeautifulSoup

        text = list_html.decode("utf-8", errors="replace") if isinstance(list_html, bytes) else str(list_html)
        array_match = re.search(r"JBL\.embed_v2\['jobs'\]\s*=\s*(\[.*?\]);", text, re.DOTALL)
        if not array_match:
            return text

        details: dict[str, str] = {}
        for job_id, path in re.findall(
            r"id:\s*'([^']+)'[^{]*?url:\s*'([^']+)'", array_match.group(1)
        ):
            if job_id in details:
                continue
            page_url = f"https://emp.jobylon.com{path}"
            try:
                body, _, _ = self._http_get(page_url, timeout=timeout)
                soup = BeautifulSoup(
                    body.decode("utf-8", errors="replace") if isinstance(body, bytes) else str(body),
                    "html.parser",
                )
                description = self._json_ld_job_description(soup)
                if description:
                    details[job_id] = description
            except RuntimeError as exc:
                logger.warning("Jobylon detail failed for %s: %s", page_url, exc)
            self._pause_between_details()

        return self._append_detail_script(BeautifulSoup(text, "html.parser"), details)

    @staticmethod
    def _json_ld_job_description(soup: Any) -> str | None:
        for tag in soup.select('script[type="application/ld+json"]'):
            try:
                data = json.loads(tag.string or "{}")
            except json.JSONDecodeError:
                continue
            for entry in data if isinstance(data, list) else [data]:
                if isinstance(entry, dict) and entry.get("@type") == "JobPosting":
                    description = entry.get("description")
                    if isinstance(description, str) and description.strip():
                        return description.strip()
        return None

    @staticmethod
    def _append_detail_script(soup: Any, details: dict[str, str]) -> str:
        if details:
            script = soup.new_tag("script", type="application/x-bronze-detail")
            script.string = json.dumps(details)
            (soup.body or soup).append(script)
        return str(soup)

    def _fetch_and_archive_one(self, url: str, timeout: float = 30.0) -> str:
        if self.render:
            body: Any = self._render_html(url, timeout=timeout)
            status, content_type = 200, "text/html"
        elif self.paginate.get("param"):
            body = self._fetch_paginated(url, timeout=timeout)
            status, content_type = 200, "text/html"
        else:
            body, status, content_type = self._http_get(
                url,
                timeout=timeout,
                method=self.request_method,
                data=self.request_body,
            )
        if self.detail:
            if self.list_strategy == "jobylon":
                body = self._attach_jobylon_details(body, timeout=timeout)
            elif self.list_config.get("item") and self.detail.get("description"):
                body = self._attach_html_details(body, base_url=url, timeout=timeout)
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
            self._pause_between_details()
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
        # Workday's CXS bot-defence is stricter on the per-job GET than the list
        # POST: it wants a JSON Accept and a Referer back to the careers site.
        detail_headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Referer": self._workday_referer(list_url),
            "Origin": urlunsplit((*urlsplit(list_url)[:2], "", "", "")),
            "X-Requested-With": "XMLHttpRequest",
        }
        for posting in postings:
            external_path = (
                posting.get("externalPath") if isinstance(posting, dict) else None
            )
            if not external_path:
                continue
            detail_url = f"{detail_root}{external_path}"
            try:
                detail_body, _, _ = self._http_get(
                    detail_url, timeout=timeout, extra_headers=detail_headers
                )
                detail = json.loads(detail_body)
            except (RuntimeError, json.JSONDecodeError) as exc:
                logger.warning("Workday detail failed for %s: %s", external_path, exc)
                continue
            if isinstance(detail, dict):
                posting["jobPostingDetail"] = detail
            self._pause_between_details()

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
            self._pause_between_details()
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

    @staticmethod
    def _workday_referer(list_url: str) -> str:
        """External careers URL for the tenant, used as the detail-GET Referer.

        ``.../wday/cxs/<tenant>/<site>/jobs`` -> ``https://<host>/<site>``.
        """
        parts = urlsplit(list_url)
        segments = [seg for seg in parts.path.split("/") if seg]
        site = segments[-2] if len(segments) >= 2 and segments[-1] == "jobs" else ""
        return urlunsplit((parts.scheme, parts.netloc, f"/{site}", "", ""))

    @staticmethod
    def _pause_between_details() -> None:
        time.sleep(random.uniform(*DETAIL_PAUSE_RANGE))

    def _http_get(
        self,
        url: str,
        timeout: float = 30.0,
        no_retries: int = 3,
        method: str = "GET",
        data: bytes | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> tuple[bytes, int, str]:
        parts = urlsplit(url)
        headers = {
            "Accept": "application/json, text/html;q=0.9, */*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "User-Agent": USER_AGENT,
            "Referer": urlunsplit((parts.scheme, parts.netloc, "/", "", "")),
        }
        if data is not None:
            headers["Content-Type"] = "application/json"
        if extra_headers:
            headers.update(extra_headers)
        job_request = Request(url, data=data, method=method, headers=headers)
        for attempt in range(1, no_retries + 1):
            try:
                with urlopen(job_request, timeout=timeout) as response:
                    body = response.read()
                    status = getattr(response, "status", None) or response.getcode()
                    content_type = response.headers.get("Content-Type") or ""
                    return body, int(status), content_type
            except HTTPError as exc:
                retryable = exc.code in RETRYABLE_STATUS or 500 <= exc.code < 600
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
