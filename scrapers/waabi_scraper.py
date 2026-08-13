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


class WaabiScraper(BaseJobScraper):
    company_name = "Waabi"
    ats_name = "Lever"
    output_filename = "waabi_jobs.json"
    api_url = "https://api.lever.co/v0/postings/waabi?mode=json"

    def fetch_jobs(self, timeout: float = 30.0) -> list[dict[str, Any]]:
        payload = self.fetch_json(self.api_url, timeout=timeout)
        if not isinstance(payload, list):
            raise ValueError("Lever returned JSON, but the top-level value was not a list.")
        if not all(isinstance(job, dict) for job in payload):
            raise ValueError("Lever returned an invalid Waabi job record.")
        return payload

    def normalize_job(
        self, job: dict[str, Any], collected_at: str
    ) -> dict[str, Any]:
        categories = job.get("categories")
        if not isinstance(categories, dict):
            categories = {}

        all_locations = categories.get("allLocations")
        if not isinstance(all_locations, list):
            all_locations = []
        all_locations = [
            self.clean_text(location) for location in all_locations if location
        ]

        description = self.clean_text(job.get("descriptionPlain"))
        if not description:
            description = self.html_to_text(job.get("description"))

        location = self.clean_text(categories.get("location"))
        if not location and all_locations:
            location = ", ".join(all_locations)

        salary_range = job.get("salaryRange")
        if not isinstance(salary_range, dict):
            salary_range = None

        return {
            "company": self.company_name,
            "job_id": self.clean_text(job.get("id")),
            "job_title": self.clean_text(job.get("text")),
            "location": location,
            "all_locations": all_locations,
            "country_code": self.clean_text(job.get("country")),
            "team": self.clean_text(categories.get("team")),
            "department": self.clean_text(categories.get("department")),
            "commitment": self.clean_text(categories.get("commitment")),
            "workplace_type": self.clean_text(job.get("workplaceType")),
            "description": description,
            "salary_range": salary_range,
            "posting_date": self.to_utc_iso8601(
                job.get("createdAt"), epoch_milliseconds=True
            ),
            "source_url": self.clean_text(job.get("hostedUrl")),
            "apply_url": self.clean_text(job.get("applyUrl")),
            "collection_method": "API",
            "ats": self.ats_name,
            "collected_at": collected_at,
        }

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    scraper = WaabiScraper()
    parser = build_common_parser(
        "Download Waabi's public Lever jobs as normalized JSON.",
        scraper.default_output,
    )
    return validate_common_args(parser, parser.parse_args(argv))


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return WaabiScraper().execute(args.output, timeout=args.timeout)


if __name__ == "__main__":
    raise SystemExit(main())
