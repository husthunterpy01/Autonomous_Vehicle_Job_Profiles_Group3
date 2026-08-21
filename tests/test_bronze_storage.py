from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch
from uuid import UUID

from scrapers.base_scraper import BaseJobScraper
from scrapers.bosch_scraper import BoschScraper
from scrapers.bronze_storage import BronzeStorage, BronzeStorageError
from scrapers.stackav_scraper import StackAVScraper
from scrapers.waabi_scraper import WaabiScraper

SCRAPE_TIMESTAMP = "2026-08-21T04:15:30.123456Z"


class IntegrationScraper(BaseJobScraper):
    company_name = "Example Company"
    ats_name = "ExampleATS"
    output_filename = "example.json"

    def __init__(
        self, raw_job: dict[str, Any], bronze_storage: BronzeStorage
    ) -> None:
        super().__init__(bronze_storage=bronze_storage)
        self.raw_job = raw_job
        self.bronze_existed_before_normalization = False

    def fetch_jobs(self, timeout: float = 30.0) -> list[dict[str, Any]]:
        return [self.raw_job]

    def normalize_job(
        self, job: dict[str, Any], collected_at: str
    ) -> dict[str, Any]:
        self.bronze_existed_before_normalization = any(
            self.bronze_storage.root.rglob("*.json")
        )
        return {
            "company": self.company_name,
            "job_id": str(job["id"]),
            "job_title": "Engineer",
            "location": "Perth",
            "description": "Normalized description",
            "posting_date": "2026-08-21T00:00:00Z",
            "source_url": self.source_url_for_job(job),
            "collection_method": "API",
            "ats": self.ats_name,
            "collected_at": collected_at,
        }

    def source_url_for_job(self, job: dict[str, Any]) -> str:
        source_url = job.get("url")
        return source_url if isinstance(source_url, str) else ""


class BronzeStorageTests(unittest.TestCase):
    def test_company_scrapers_read_source_url_from_raw_job(self) -> None:
        self.assertEqual(
            WaabiScraper().source_url_for_job(
                {"hostedUrl": "https://jobs.lever.co/waabi/waabi-1"}
            ),
            "https://jobs.lever.co/waabi/waabi-1",
        )
        self.assertEqual(
            BoschScraper(max_jobs=1).source_url_for_job(
                {
                    "postingUrl": "https://jobs.smartrecruiters.com/BoschGroup/1",
                    "applyUrl": "https://example.com/ignored",
                }
            ),
            "https://jobs.smartrecruiters.com/BoschGroup/1",
        )
        self.assertEqual(
            StackAVScraper().source_url_for_job(
                {"absolute_url": "https://job-boards.greenhouse.io/stackav/jobs/1"}
            ),
            "https://job-boards.greenhouse.io/stackav/jobs/1",
        )

    def test_company_source_url_extractors_handle_missing_invalid_values(self) -> None:
        waabi = WaabiScraper()
        stackav = StackAVScraper()
        bosch = BoschScraper(max_jobs=1)

        for raw_job in ({}, {"hostedUrl": None}, {"hostedUrl": 123}):
            with self.subTest(scraper="waabi", raw_job=raw_job):
                self.assertEqual(waabi.source_url_for_job(raw_job), "")

        for raw_job in ({}, {"absolute_url": None}, {"absolute_url": 123}):
            with self.subTest(scraper="stackav", raw_job=raw_job):
                self.assertEqual(stackav.source_url_for_job(raw_job), "")

        for raw_job in (
            {},
            {"postingUrl": None, "applyUrl": None},
            {"postingUrl": 123, "applyUrl": 456},
        ):
            with self.subTest(scraper="bosch", raw_job=raw_job):
                self.assertEqual(bosch.source_url_for_job(raw_job), "")

        self.assertEqual(
            bosch.source_url_for_job(
                {
                    "postingUrl": None,
                    "applyUrl": "https://jobs.smartrecruiters.com/BoschGroup/1?oga=true",
                }
            ),
            "https://jobs.smartrecruiters.com/BoschGroup/1",
        )
        self.assertEqual(
            bosch.source_url_for_job(
                {
                    "postingUrl": 123,
                    "applyUrl": "https://jobs.smartrecruiters.com/BoschGroup/2?oga=true",
                }
            ),
            "https://jobs.smartrecruiters.com/BoschGroup/2",
        )

    def test_rejects_unsafe_invalid_and_non_utc_timestamps(self) -> None:
        invalid_timestamps = {
            "parent traversal": "../2026-08-21T04:15:30Z",
            "double parent traversal": "../../2026-08-21T04:15:30Z",
            "absolute path": "/tmp/2026-08-21T04:15:30Z",
            "backslash traversal": r"..\..\2026-08-21T04:15:30Z",
            "invalid timestamp": "not-a-timestamp",
            "non-UTC timestamp": "2026-08-21T12:15:30+08:00",
        }
        raw_job = {"id": 1, "url": "https://example.com/jobs/1"}

        with tempfile.TemporaryDirectory() as directory:
            storage = BronzeStorage(Path(directory) / "bronze")
            for label, timestamp in invalid_timestamps.items():
                with (
                    self.subTest(case=label),
                    self.assertLogs(
                        "scrapers.bronze_storage", level="ERROR"
                    ),
                    self.assertRaisesRegex(
                        BronzeStorageError, "valid UTC ISO-8601"
                    ),
                ):
                    storage.persist_jobs(
                        [raw_job],
                        source_company="Example",
                        source_url_for_job=lambda job: job["url"],
                        scrape_timestamp=timestamp,
                    )

            self.assertFalse(any(storage.root.rglob("*.json")))

    def test_unsafe_company_name_cannot_escape_bronze_root(self) -> None:
        raw_job = {"id": 1, "url": "https://example.com/jobs/1"}

        with tempfile.TemporaryDirectory() as directory:
            storage = BronzeStorage(Path(directory) / "bronze")
            path = storage.persist_jobs(
                [raw_job],
                source_company="../../Example\\Company",
                source_url_for_job=lambda job: job["url"],
                scrape_timestamp=SCRAPE_TIMESTAMP,
            )[0]

            self.assertTrue(path.resolve().is_relative_to(storage.root.resolve()))
            self.assertEqual(path.parent.parent.name, "example-company")

    def test_persists_unmodified_raw_payload_with_required_metadata(self) -> None:
        raw_job = {
            "id": 123,
            "title": "R&D Engineer",
            "content": "&lt;p&gt;Keep &amp; preserve&lt;/p&gt;",
            "nested": {"unchanged": [None, True, 3.5]},
            "url": "https://example.com/jobs/123?source=ats",
        }

        with tempfile.TemporaryDirectory() as directory:
            storage = BronzeStorage(Path(directory) / "bronze")
            paths = storage.persist_jobs(
                [raw_job],
                source_company="Example Company",
                source_url_for_job=lambda job: job["url"],
                scrape_timestamp=SCRAPE_TIMESTAMP,
            )

            self.assertEqual(len(paths), 1)
            self.assertEqual(
                paths[0].parent,
                Path(directory) / "bronze" / "example-company" / "2026-08-21",
            )
            record = json.loads(paths[0].read_text(encoding="utf-8"))

        self.assertEqual(record["source_company"], "Example Company")
        self.assertEqual(record["source_url"], raw_job["url"])
        self.assertEqual(record["scrape_timestamp"], SCRAPE_TIMESTAMP)
        self.assertEqual(record["raw_payload"], raw_job)
        self.assertRegex(
            record["record_id"],
            r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
        )

    def test_duplicate_capture_creates_new_record_without_overwrite(self) -> None:
        raw_job = {"id": "same", "url": "https://example.com/jobs/same"}

        with tempfile.TemporaryDirectory() as directory:
            storage = BronzeStorage(Path(directory) / "bronze")
            first_path = storage.persist_jobs(
                [raw_job],
                source_company="Example",
                source_url_for_job=lambda job: job["url"],
                scrape_timestamp=SCRAPE_TIMESTAMP,
            )[0]
            first_contents = first_path.read_text(encoding="utf-8")
            second_path = storage.persist_jobs(
                [raw_job],
                source_company="Example",
                source_url_for_job=lambda job: job["url"],
                scrape_timestamp=SCRAPE_TIMESTAMP,
            )[0]

            self.assertNotEqual(first_path, second_path)
            self.assertEqual(first_path.read_text(encoding="utf-8"), first_contents)
            records = [
                json.loads(path.read_text(encoding="utf-8"))
                for path in sorted(storage.root.rglob("*.json"))
            ]

        self.assertEqual(len(records), 2)
        self.assertNotEqual(records[0]["record_id"], records[1]["record_id"])
        self.assertEqual(
            {(record["source_url"], record["scrape_timestamp"]) for record in records},
            {(raw_job["url"], SCRAPE_TIMESTAMP)},
        )

    def test_record_id_collision_does_not_delete_or_replace_existing_record(self) -> None:
        raw_job = {"id": "same", "url": "https://example.com/jobs/same"}
        fixed_id = UUID("550e8400-e29b-41d4-a716-446655440000")

        with tempfile.TemporaryDirectory() as directory:
            storage = BronzeStorage(Path(directory) / "bronze")
            with patch("scrapers.bronze_storage.uuid4", return_value=fixed_id):
                path = storage.persist_jobs(
                    [raw_job],
                    source_company="Example",
                    source_url_for_job=lambda job: job["url"],
                    scrape_timestamp=SCRAPE_TIMESTAMP,
                )[0]
                original_contents = path.read_text(encoding="utf-8")
                with (
                    self.assertLogs(
                        "scrapers.bronze_storage", level="ERROR"
                    ),
                    self.assertRaises(BronzeStorageError),
                ):
                    storage.persist_jobs(
                        [raw_job],
                        source_company="Example",
                        source_url_for_job=lambda job: job["url"],
                        scrape_timestamp=SCRAPE_TIMESTAMP,
                    )

            self.assertTrue(path.exists())
            self.assertEqual(path.read_text(encoding="utf-8"), original_contents)
            self.assertFalse(any(storage.root.rglob("*.tmp")))

    def test_publication_uses_complete_closed_temporary_file(self) -> None:
        raw_job = {"id": 1, "url": "https://example.com/jobs/1"}
        real_link = os.link

        def inspect_then_publish(source: Path, destination: Path) -> None:
            source_path = Path(source)
            destination_path = Path(destination)
            self.assertEqual(source_path.suffix, ".tmp")
            self.assertEqual(destination_path.suffix, ".json")
            self.assertFalse(destination_path.exists())
            json.loads(source_path.read_text(encoding="utf-8"))
            real_link(source_path, destination_path)

        with tempfile.TemporaryDirectory() as directory:
            storage = BronzeStorage(Path(directory) / "bronze")
            with patch(
                "scrapers.bronze_storage.os.link",
                side_effect=inspect_then_publish,
            ):
                path = storage.persist_jobs(
                    [raw_job],
                    source_company="Example",
                    source_url_for_job=lambda job: job["url"],
                    scrape_timestamp=SCRAPE_TIMESTAMP,
                )[0]

            self.assertTrue(path.exists())
            self.assertFalse(any(storage.root.rglob("*.tmp")))

    def test_serialization_failure_leaves_no_json_or_temporary_file(self) -> None:
        raw_job = {"id": 1, "url": "https://example.com/jobs/1"}

        def fail_after_partial_write(
            _record: dict[str, Any], file: Any, **_kwargs: Any
        ) -> None:
            file.write('{"partial":')
            raise TypeError("simulated serialization failure")

        with tempfile.TemporaryDirectory() as directory:
            storage = BronzeStorage(Path(directory) / "bronze")
            with (
                patch(
                    "scrapers.bronze_storage.json.dump",
                    side_effect=fail_after_partial_write,
                ),
                self.assertLogs(
                    "scrapers.bronze_storage", level="ERROR"
                ),
                self.assertRaises(BronzeStorageError),
            ):
                storage.persist_jobs(
                    [raw_job],
                    source_company="Example",
                    source_url_for_job=lambda job: job["url"],
                    scrape_timestamp=SCRAPE_TIMESTAMP,
                )

            self.assertFalse(any(storage.root.rglob("*.json")))
            self.assertFalse(any(storage.root.rglob("*.tmp")))
            self.assertFalse(
                any(path.is_file() for path in storage.root.rglob("*"))
            )

    def test_persistence_failure_is_logged_and_raised(self) -> None:
        raw_job = {"id": "missing-url"}

        with tempfile.TemporaryDirectory() as directory:
            storage = BronzeStorage(Path(directory) / "bronze")
            with (
                self.assertLogs("scrapers.bronze_storage", level="ERROR") as logs,
                self.assertRaises(BronzeStorageError),
            ):
                storage.persist_jobs(
                    [raw_job],
                    source_company="Example",
                    source_url_for_job=lambda _job: "",
                    scrape_timestamp=SCRAPE_TIMESTAMP,
                )

        self.assertIn("Bronze persistence failed", "\n".join(logs.output))
        self.assertIn("record_id=", "\n".join(logs.output))

    def test_scrape_persists_bronze_before_normalization(self) -> None:
        raw_job = {
            "id": 1,
            "url": "https://example.com/jobs/1",
            "html": "<p>Raw &amp; untouched</p>",
        }

        with tempfile.TemporaryDirectory() as directory:
            storage = BronzeStorage(Path(directory) / "bronze")
            scraper = IntegrationScraper(raw_job, storage)
            normalized = scraper.scrape()
            bronze_path = next(storage.root.rglob("*.json"))
            bronze_record = json.loads(bronze_path.read_text(encoding="utf-8"))

        self.assertTrue(scraper.bronze_existed_before_normalization)
        self.assertEqual(bronze_record["raw_payload"], raw_job)
        self.assertEqual(normalized[0]["description"], "Normalized description")

    def test_separate_scrape_runs_persist_their_utc_timestamps(self) -> None:
        raw_job = {"id": 1, "url": "https://example.com/jobs/1"}
        first_run = datetime(2026, 8, 21, 4, 15, 30, 1, tzinfo=timezone.utc)
        second_run = datetime(2026, 8, 21, 4, 16, 30, 2, tzinfo=timezone.utc)

        with tempfile.TemporaryDirectory() as directory:
            storage = BronzeStorage(Path(directory) / "bronze")
            scraper = IntegrationScraper(raw_job, storage)
            with patch("scrapers.base_scraper.datetime") as mocked_datetime:
                mocked_datetime.now.side_effect = [first_run, second_run]
                scraper.scrape()
                scraper.scrape()

            records = [
                json.loads(path.read_text(encoding="utf-8"))
                for path in storage.root.rglob("*.json")
            ]

        self.assertEqual(len(records), 2)
        self.assertEqual(
            {record["scrape_timestamp"] for record in records},
            {
                "2026-08-21T04:15:30.000001Z",
                "2026-08-21T04:16:30.000002Z",
            },
        )


class BronzeFailureIntegrationTests(unittest.TestCase):
    def test_bronze_failure_keeps_normalized_output_and_exit_code(self) -> None:
        raw_job = {"id": 1, "url": "https://example.com/jobs/1"}

        with tempfile.TemporaryDirectory() as directory:
            directory_path = Path(directory)
            blocked_root = directory_path / "bronze"
            blocked_root.write_text("not a directory", encoding="utf-8")
            output_path = directory_path / "normalized.json"
            output_path.write_text('{"previous": true}\n', encoding="utf-8")
            scraper = IntegrationScraper(raw_job, BronzeStorage(blocked_root))

            with (
                self.assertLogs("scrapers.base_scraper", level="ERROR"),
                patch("builtins.print"),
            ):
                result = scraper.execute(output_path)

            self.assertEqual(result, 1)
            self.assertEqual(
                json.loads(output_path.read_text(encoding="utf-8")),
                {"previous": True},
            )

    def test_bosch_logs_each_detail_failure_and_partial_summary(self) -> None:
        scraper = BoschScraper(max_jobs=2)
        summaries = [{"id": "ok"}, {"id": "failed"}]

        def fetch_detail(posting_id: str, timeout: float) -> dict[str, Any]:
            if posting_id == "failed":
                raise RuntimeError("detail endpoint unavailable")
            return {"id": posting_id}

        with (
            patch.object(scraper, "_fetch_summaries", return_value=summaries),
            patch.object(scraper, "_fetch_detail", side_effect=fetch_detail),
            self.assertLogs("scrapers.bosch_scraper", level="ERROR") as logs,
            self.assertRaisesRegex(RuntimeError, "detail scrape was partial"),
        ):
            scraper.fetch_jobs(timeout=5.0)

        output = "\n".join(logs.output)
        self.assertIn("posting_id=failed", output)
        self.assertIn("succeeded=1 failed=1", output)


if __name__ == "__main__":
    unittest.main()
