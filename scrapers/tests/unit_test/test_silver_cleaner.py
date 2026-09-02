from datetime import UTC, datetime

from scrapers.service.silver_cleaning import SilverCleaner


def _record(**overrides):
    record = {
        "id": 101,
        "ats_name": "lever",
        "company_name": "Waabi",
        "job_name": "Software Engineer",
        "job_description": "<p>Build <strong>safe</strong> software.</p>",
        "location": "Toronto, ON | Remote | Toronto, ON",
        "job_url": "https://jobs.lever.co/waabi/abc",
        "job_uploaded_at": 1_690_000_000_000,
        "employment_type": "FullTime",
        "ingested_at": "2026-09-01T10:00:00Z",
        "rn": 7,
    }
    record.update(overrides)
    return record


def test_clean_record_keeps_id_ignores_rn_and_normalizes_fields():
    cleaned = SilverCleaner.clean_record(_record())

    assert cleaned is not None
    assert cleaned["id"] == "101"
    assert "rn" not in cleaned
    assert cleaned["job_description"] == "Build safe software."
    assert cleaned["locations"] == ("Toronto, ON", "Remote")
    assert cleaned["employment_type"] == "full-time"
    assert cleaned["job_uploaded_at"] == datetime(2023, 7, 22, 4, 26, 40, tzinfo=UTC)


def test_clean_records_removes_missing_titles():
    assert SilverCleaner.clean_records([_record(job_name="  ")]) == []


def test_clean_records_removes_missing_descriptions():
    assert SilverCleaner.clean_records([_record(job_description="  ")]) == []


def test_clean_record_accepts_future_job_id_column_as_source_id():
    cleaned = SilverCleaner.clean_record(_record(job_id="lever-123"))

    assert cleaned is not None
    assert cleaned["source_job_id"] == "lever-123"


def test_deduplication_prefers_source_job_id_then_url():
    records = [
        _record(id=1, source_job_id="job-42", job_url="https://example.test/old"),
        _record(id=2, source_job_id="job-42", job_url="https://example.test/new", department="AI"),
        _record(id=3, source_job_id=None, job_url="https://example.test/shared"),
        _record(id=4, source_job_id=None, job_url="https://example.test/shared/"),
    ]

    cleaned = SilverCleaner.clean_records(records)

    assert [record["id"] for record in cleaned] == ["2", "3"]


def test_fallback_key_treats_ordered_multi_locations_as_one_posting():
    records = [
        _record(id=1, source_job_id=None, job_url=None, location="Perth | Remote"),
        _record(id=2, source_job_id=None, job_url=None, location="remote | perth"),
    ]

    cleaned = SilverCleaner.clean_records(records)

    assert len(cleaned) == 1


def test_deduplication_keeps_more_complete_then_latest_record():
    records = [
        _record(id=1, ingested_at="2026-09-01T12:00:00Z", job_description=None),
        _record(id=2, ingested_at="2026-09-01T10:00:00Z", headquarter="Canada"),
    ]

    cleaned = SilverCleaner.clean_records(records)

    assert cleaned[0]["id"] == "2"


def test_invalid_timestamp_becomes_null_instead_of_breaking_batch():
    cleaned = SilverCleaner.clean_record(_record(job_uploaded_at="unknown"))

    assert cleaned is not None
    assert cleaned["job_uploaded_at"] is None
