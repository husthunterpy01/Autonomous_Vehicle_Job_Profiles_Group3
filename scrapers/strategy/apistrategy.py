from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import yaml

from scrapers.config.minio import MinioConfig
from scrapers.response_archive import ResponseArchive
from scrapers.strategy.fetchstrategy import FetchStrategy

ATS_PATH = "./scrapers/data/ats_sources.yaml"


class APIStrategy(FetchStrategy):
    def __init__(self, ats_name: str, slug: str, company_name: str) -> None:
        super().__init__()
        self.ats_name = ats_name
        self.slug = slug
        self.company_name = company_name

    def fetch_postings( self, max_jobs: int, timeout: float = 30.0) -> list[dict[str, Any]]:
        with open(ATS_PATH, "r") as file:
            ats_config = yaml.safe_load(file)

        sources = ats_config["ats_sources"]
        if self.ats_name not in sources:
            raise ValueError(
                f"ATS name is not available in the ATS list: {self.ats_name}"
            )

        job_url = sources[self.ats_name]["api_base"].format(slug=self.slug)
        job_payload = self.fetch_api_json_data(url=job_url, timeout=timeout)
        jobs = self._extract_jobs(job_payload)

        archive = ResponseArchive(MinioConfig())
        archive.save_raw_response(
            company_name=self.company_name,
            collected_at=datetime.now(timezone.utc),
            raw_response=job_payload,
            source="api",
            url=job_url,
            content_type="application/json",
        )
        return jobs[:max_jobs]

    def _extract_jobs(self, job_payload: Any) -> list[dict[str, Any]]:
        if self.ats_name in {"greenhouse", "ashby"}:
            if not isinstance(job_payload, dict):
                raise ValueError("Job is in an invalid JSON Response")
            job_list = job_payload.get("jobs")
            if not isinstance(job_list, list):
                raise ValueError(f"{self.ats_name} API does not contain the job list")
            if not all(isinstance(job, dict) for job in job_list):
                raise ValueError(f"{self.ats_name} returned an invalid job record.")
            if self.ats_name == "greenhouse":
                meta = job_payload.get("meta")
                total = meta.get("total") if isinstance(meta, dict) else None
                if isinstance(total, int) and total != len(job_list):
                    raise ValueError(
                        f"Greenhouse reported {total} jobs but returned "
                        f"{len(job_list)} records."
                    )
            return job_list

        if isinstance(job_payload, list):
            if not all(isinstance(job, dict) for job in job_payload):
                raise ValueError(f"{self.ats_name} returned an invalid job record.")
            return job_payload

        if isinstance(job_payload, dict):
            content = job_payload.get("content")
            if isinstance(content, list):
                return content
            return [job_payload]

        raise ValueError("Job is in an invalid JSON Response")

    def fetch_api_json_data(self, url: str, timeout: float = 30.0, no_retries: int = 3) -> Any:
        # Ashby requires User-Agent for auto scraping
        job_request = Request(url,headers={"Accept": "application/json","User-Agent": "Mozilla/5.0",})
        for attempt in range(1, no_retries + 1):
            try:
                with urlopen(job_request, timeout=timeout) as response:
                    return json.load(response)
            except HTTPError as exc:
                retryable = exc.code == 429 or 500 <= exc.code < 600
                if not retryable or attempt == no_retries:
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
                if attempt == no_retries:
                    raise RuntimeError(
                        f"Could not connect to {self.ats_name}: {exc.reason}"
                    ) from exc
                time.sleep(2 ** (attempt - 1))

        raise RuntimeError(f"{self.ats_name} request failed after all retries.")
