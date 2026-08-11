from __future__ import annotations

import argparse
from typing import Any

if __package__:
    from .base_scraper import (
        BaseJobScraper,
        build_common_parser,
        validate_common_args,
    )
else:
    from base_scraper import (  # type: ignore[no-redef]
        BaseJobScraper,
        build_common_parser,
        validate_common_args,
    )


class StackAVScraper(BaseJobScraper):
    company_name = "Stack AV"
    ats_name = "Greenhouse"
    output_filename = "stackav_jobs.json"
    api_url = "https://boards-api.greenhouse.io/v1/boards/stackav/jobs?content=true"

    def fetch_jobs(self, timeout: float = 30.0) -> list[dict[str, Any]]:
        payload = self.fetch_json(self.api_url, timeout=timeout)
        if not isinstance(payload, dict):
            raise ValueError("Greenhouse returned an invalid JSON response.")

        jobs = payload.get("jobs")
        if not isinstance(jobs, list):
            raise ValueError("Greenhouse response did not contain a jobs list.")
        if not all(isinstance(job, dict) for job in jobs):
            raise ValueError("Greenhouse returned an invalid Stack AV job record.")

        meta = payload.get("meta")
        total = meta.get("total") if isinstance(meta, dict) else None
        if isinstance(total, int) and total != len(jobs):
            raise ValueError(
                f"Greenhouse reported {total} jobs but returned {len(jobs)} records."
            )
        return jobs

    def normalize_job(
        self, job: dict[str, Any], collected_at: str
    ) -> dict[str, Any]:
        location_value = job.get("location")
        location = (
            self.clean_text(location_value.get("name"))
            if isinstance(location_value, dict)
            else ""
        )
        departments = self._names(job.get("departments"))
        offices = self._names(job.get("offices"))
        source_url = self.clean_text(job.get("absolute_url"))

        return {
            "company": self.company_name,
            "job_id": self.clean_text(job.get("id")),
            "job_title": self.clean_text(job.get("title")),
            "location": location,
            "all_locations": [location] if location else [],
            "country_code": "",
            "team": departments[0] if departments else "",
            "department": ", ".join(departments),
            "commitment": "",
            "workplace_type": self._workplace_type(location, offices),
            "description": self.html_to_text(job.get("content")),
            "salary_range": None,
            "posting_date": self.clean_text(job.get("first_published")),
            "source_url": source_url,
            "apply_url": source_url,
            "collection_method": "API",
            "ats": self.ats_name,
            "collected_at": collected_at,
            "language": self.clean_text(job.get("language")),
            "job_reference": self.clean_text(job.get("requisition_id")),
            "internal_job_id": self.clean_text(job.get("internal_job_id")),
            "updated_at": self.clean_text(job.get("updated_at")),
            "application_deadline": self.clean_text(
                job.get("application_deadline")
            ),
            "offices": offices,
        }

    @classmethod
    def _names(cls, values: Any) -> list[str]:
        if not isinstance(values, list):
            return []

        result: list[str] = []
        for value in values:
            if not isinstance(value, dict):
                continue
            name = cls.clean_text(value.get("name"))
            if name and name not in result:
                result.append(name)
        return result

    @staticmethod
    def _workplace_type(location: str, offices: list[str]) -> str:
        searchable = " ".join([location, *offices]).casefold()
        if "hybrid" in searchable:
            return "hybrid"
        if "remote" in searchable:
            return "remote"
        return "onsite"

    def scrape(self, timeout: float = 30.0) -> list[dict[str, Any]]:
        records = super().scrape(timeout=timeout)
        records.sort(key=lambda record: record["posting_date"], reverse=True)
        return records


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    scraper = StackAVScraper()
    parser = build_common_parser(
        "Download Stack AV's public Greenhouse jobs as normalized JSON.",
        scraper.default_output,
    )
    return validate_common_args(parser, parser.parse_args(argv))


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return StackAVScraper().execute(args.output, timeout=args.timeout)


if __name__ == "__main__":
    raise SystemExit(main())
