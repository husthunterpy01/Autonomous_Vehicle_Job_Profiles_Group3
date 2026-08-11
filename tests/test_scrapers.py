from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from scrapers.base_scraper import BaseJobScraper, COMMON_REQUIRED_FIELDS
from scrapers.bosch_scraper import BoschScraper
from scrapers.stackav_scraper import StackAVScraper
from scrapers.waabi_scraper import WaabiScraper


class DummyScraper(BaseJobScraper):
    company_name = "Example"
    ats_name = "ExampleATS"
    output_filename = "example.json"

    def fetch_jobs(self, timeout: float = 30.0) -> list[dict[str, Any]]:
        return []

    def normalize_job(
        self, job: dict[str, Any], collected_at: str
    ) -> dict[str, Any]:
        return job


def valid_record(job_id: str = "1") -> dict[str, Any]:
    return {
        "company": "Example",
        "job_id": job_id,
        "job_title": "Engineer",
        "location": "Perth",
        "description": "Build safe software.",
        "posting_date": "2026-08-11T00:00:00Z",
        "source_url": "https://example.com/jobs/1",
        "collection_method": "API",
        "ats": "ExampleATS",
        "collected_at": "2026-08-11T01:00:00Z",
    }


class BaseJobScraperTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scraper = DummyScraper()

    def test_html_to_text_decodes_nested_entities(self) -> None:
        encoded = "&amp;lt;p&amp;gt;Build &amp;lt;strong&amp;gt;safe&amp;lt;/strong&amp;gt; software.&amp;lt;/p&amp;gt;"
        self.assertEqual(
            self.scraper.html_to_text(encoded),
            "Build safe software.",
        )

    def test_validation_rejects_duplicate_ids(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate Example job ID"):
            self.scraper.validate_records([valid_record(), valid_record()])

    def test_validation_rejects_missing_required_fields(self) -> None:
        record = valid_record()
        record["description"] = ""
        with self.assertRaisesRegex(ValueError, "description"):
            self.scraper.validate_records([record])

    def test_atomic_json_writer_creates_valid_utf8(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "jobs.json"
            records = [{"title": "Ingénieur"}]
            self.scraper.write_json(records, output)
            self.assertEqual(
                json.loads(output.read_text(encoding="utf-8")),
                records,
            )
            self.assertFalse(output.with_suffix(".json.tmp").exists())


class CompanyNormalizerTests(unittest.TestCase):
    collected_at = "2026-08-11T01:00:00Z"

    def assert_common_schema(self, scraper: BaseJobScraper, record: dict) -> None:
        self.assertTrue(set(COMMON_REQUIRED_FIELDS).issubset(record))
        scraper.validate_records([record])

    def test_waabi_normalizer(self) -> None:
        scraper = WaabiScraper()
        raw = {
            "id": "waabi-1",
            "text": "Research Scientist",
            "createdAt": 1_720_000_000_000,
            "categories": {
                "location": "Toronto, Canada",
                "allLocations": ["Toronto, Canada"],
                "team": "AI",
                "commitment": "Full-time",
            },
            "workplaceType": "hybrid",
            "descriptionPlain": "Build autonomous systems.",
            "hostedUrl": "https://jobs.lever.co/waabi/waabi-1",
            "applyUrl": "https://jobs.lever.co/waabi/waabi-1/apply",
        }
        record = scraper.normalize_job(raw, self.collected_at)
        self.assertEqual(record["company"], "Waabi")
        self.assertEqual(record["ats"], "Lever")
        self.assertEqual(record["posting_date"], "2024-07-03T09:46:40Z")
        self.assert_common_schema(scraper, record)

    def test_bosch_normalizer(self) -> None:
        scraper = BoschScraper(max_jobs=1)
        raw = {
            "id": "bosch-1",
            "name": "ADAS Software Engineer",
            "releasedDate": "2026-08-10T01:02:03.000Z",
            "postingUrl": "https://jobs.smartrecruiters.com/BoschGroup/bosch-1",
            "applyUrl": "https://jobs.smartrecruiters.com/BoschGroup/bosch-1?oga=true",
            "location": {
                "fullLocation": "Stuttgart, Germany",
                "country": "de",
                "hybrid": True,
            },
            "function": {"label": "Engineering"},
            "typeOfEmployment": {"label": "Full-time"},
            "jobAd": {
                "sections": {
                    "jobDescription": {
                        "title": "Job Description",
                        "text": "<p>Build safe ADAS software.</p>",
                    }
                }
            },
        }
        record = scraper.normalize_job(raw, self.collected_at)
        self.assertEqual(record["company"], "Bosch")
        self.assertEqual(record["ats"], "SmartRecruiters")
        self.assertEqual(record["workplace_type"], "hybrid")
        self.assert_common_schema(scraper, record)

    def test_stackav_normalizer(self) -> None:
        scraper = StackAVScraper()
        raw = {
            "id": 123,
            "title": "Software Engineer, Perception",
            "first_published": "2026-08-01T10:00:00-04:00",
            "location": {"name": "Pittsburgh, PA or Remote"},
            "absolute_url": "https://job-boards.greenhouse.io/stackav/jobs/123",
            "content": "&lt;p&gt;Build &lt;strong&gt;safe&lt;/strong&gt; perception software.&lt;/p&gt;",
            "departments": [{"name": "Autonomy"}],
            "offices": [{"name": "Remote"}],
        }
        record = scraper.normalize_job(raw, self.collected_at)
        self.assertEqual(record["company"], "Stack AV")
        self.assertEqual(record["ats"], "Greenhouse")
        self.assertEqual(record["workplace_type"], "remote")
        self.assertEqual(record["description"], "Build safe perception software.")
        self.assert_common_schema(scraper, record)


if __name__ == "__main__":
    unittest.main()
