from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from itertools import repeat
from typing import Any
from urllib.parse import urlencode

from scrapers.base_scraper import (
    BaseJobScraper,
    build_common_parser,
    validate_common_args,
)


class BoschScraper(BaseJobScraper):
    company_name = "Bosch"
    ats_name = "SmartRecruiters"
    output_filename = "bosch_jobs.json"
    company_identifier = "BoschGroup"
    api_base = (
        "https://api.smartrecruiters.com/v1/companies/"
        f"{company_identifier}/postings"
    )
    page_size = 100
    detail_workers = 5

    def __init__(self, max_jobs: int = 100) -> None:
        super().__init__()
        if max_jobs < 1:
            raise ValueError("max_jobs must be at least 1")
        self.max_jobs = max_jobs

    def fetch_jobs(self, timeout: float = 30.0) -> list[dict[str, Any]]:
        summaries = self._fetch_summaries(timeout=timeout)
        posting_ids = [self.clean_text(summary.get("id")) for summary in summaries]
        if any(not posting_id for posting_id in posting_ids):
            raise ValueError("A Bosch posting summary was missing its job ID.")

        with ThreadPoolExecutor(max_workers=self.detail_workers) as executor:
            return list(
                executor.map(self._fetch_detail, posting_ids, repeat(timeout))
            )

    def _fetch_detail(
        self, posting_id: str, timeout: float = 30.0
    ) -> dict[str, Any]:
        """Fetch and validate one SmartRecruiters job-detail response."""

        payload = self.fetch_json(f"{self.api_base}/{posting_id}", timeout=timeout)
        if not isinstance(payload, dict):
            raise ValueError("SmartRecruiters returned an invalid job detail.")
        return payload

    def _fetch_summaries(self, timeout: float) -> list[dict[str, Any]]:
        summaries: list[dict[str, Any]] = []
        offset = 0

        while len(summaries) < self.max_jobs:
            requested = min(self.page_size, self.max_jobs - len(summaries))
            query = urlencode(
                {"limit": requested, "offset": offset, "destination": "PUBLIC"}
            )
            payload = self.fetch_json(f"{self.api_base}?{query}", timeout=timeout)
            if not isinstance(payload, dict):
                raise ValueError("SmartRecruiters returned an invalid postings page.")

            page = payload.get("content")
            if not isinstance(page, list):
                raise ValueError(
                    "SmartRecruiters response did not contain a postings list."
                )
            if not all(isinstance(item, dict) for item in page):
                raise ValueError("SmartRecruiters returned an invalid posting summary.")

            summaries.extend(page)
            if not page:
                break

            offset += len(page)
            total_found = payload.get("totalFound")
            if isinstance(total_found, int) and offset >= total_found:
                break

        return summaries[: self.max_jobs]

    def normalize_job(
        self, job: dict[str, Any], collected_at: str
    ) -> dict[str, Any]:
        location = job.get("location")
        if not isinstance(location, dict):
            location = {}

        full_location = self.clean_text(location.get("fullLocation"))
        if not full_location:
            parts = [
                self.clean_text(location.get("city")),
                self.clean_text(location.get("region")),
                self.clean_text(location.get("country")),
            ]
            full_location = ", ".join(part for part in parts if part)

        source_url = self.clean_text(job.get("postingUrl"))
        apply_url = self.clean_text(job.get("applyUrl"))
        if not source_url:
            source_url = apply_url.split("?", maxsplit=1)[0]

        language = job.get("language")
        function = self.label(job.get("function"))

        return {
            "company": self.company_name,
            "job_id": self.clean_text(job.get("id")),
            "job_title": self.clean_text(job.get("name")),
            "location": full_location,
            "all_locations": [full_location] if full_location else [],
            "country_code": self.clean_text(location.get("country")),
            "team": function,
            "department": self.label(job.get("department")),
            "commitment": self.label(job.get("typeOfEmployment")),
            "workplace_type": self._workplace_type(location),
            "description": self._build_description(job),
            "salary_range": None,
            "posting_date": self.to_utc_iso8601(job.get("releasedDate")),
            "source_url": source_url,
            "apply_url": apply_url,
            "collection_method": "API",
            "ats": self.ats_name,
            "collected_at": collected_at,
            "language": (
                self.clean_text(language.get("code"))
                if isinstance(language, dict)
                else ""
            ),
            "job_reference": self.clean_text(job.get("refNumber")),
            "function": function,
            "experience_level": self.label(job.get("experienceLevel")),
            "industry": self.label(job.get("industry")),
        }

    def _build_description(self, job: dict[str, Any]) -> str:
        job_ad = job.get("jobAd")
        sections = job_ad.get("sections") if isinstance(job_ad, dict) else None
        if not isinstance(sections, dict):
            return ""

        parts: list[str] = []
        for key in (
            "companyDescription",
            "jobDescription",
            "qualifications",
            "additionalInformation",
        ):
            section = sections.get(key)
            if not isinstance(section, dict):
                continue
            title = self.clean_text(section.get("title"))
            text = self.html_to_text(section.get("text"))
            if text:
                parts.append(f"{title}\n{text}" if title else text)
        return "\n\n".join(parts)

    @staticmethod
    def _workplace_type(location: dict[str, Any]) -> str:
        if location.get("hybrid") is True:
            return "hybrid"
        if location.get("remote") is True:
            return "remote"
        return "onsite"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    defaults = BoschScraper()
    parser = build_common_parser(
        "Download Bosch's public SmartRecruiters jobs as normalized JSON.",
        defaults.default_output,
    )
    parser.add_argument(
        "--max-jobs",
        type=int,
        default=100,
        help="number of newest public jobs to collect (default: 100)",
    )
    args = validate_common_args(parser, parser.parse_args(argv))
    if args.max_jobs < 1:
        parser.error("--max-jobs must be at least 1")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    scraper = BoschScraper(max_jobs=args.max_jobs)
    return scraper.execute(args.output, timeout=args.timeout)


if __name__ == "__main__":
    raise SystemExit(main())
