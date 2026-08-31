import pytest

from scrapers.strategy.ats.ashbystrategy import AshbyStrategy
from scrapers.strategy.ats.greenhousestrategy import GreenhouseStrategy
from scrapers.strategy.ats.leverstrategy import LeverStrategy
from scrapers.strategy.ats.smartrecruiter import SmartRecruiterStrategy
from scrapers.strategy.registry import extract_jobs_from_payload, get_ats_adapter


def test_extract_jobs_from_greenhouse_payload():
    jobs = GreenhouseStrategy().extract_job_information(
        {"jobs": [{"id": "1", "title": "Engineer"}], "meta": {"total": 1}}
    )

    assert jobs == [{"id": "1", "title": "Engineer"}]


def test_extract_jobs_from_ashby_payload():
    jobs = AshbyStrategy().extract_job_information({"jobs": [{"id": "a1"}]})

    assert jobs == [{"id": "a1"}]


def test_extract_jobs_from_lever_list():
    jobs = LeverStrategy().extract_job_information([{"id": "abc", "text": "Engineer"}])

    assert jobs[0]["id"] == "abc"


def test_extract_jobs_from_smartrecruiters_content():
    jobs = SmartRecruiterStrategy().extract_job_information({"content": [{"id": "sr-1"}]})

    assert jobs == [{"id": "sr-1"}]


def test_extract_jobs_rejects_greenhouse_count_mismatch():
    with pytest.raises(ValueError, match="reported 2 jobs"):
        GreenhouseStrategy().extract_job_information(
            {"jobs": [{"id": "1"}], "meta": {"total": 2}}
        )


def test_extract_jobs_from_payload_uses_source_system():
    jobs = extract_jobs_from_payload(
        "greenhouse",
        {"jobs": [{"id": "1"}], "meta": {"total": 1}},
    )

    assert jobs == [{"id": "1"}]


def test_unknown_source_system_raises():
    with pytest.raises(ValueError, match="Unknown source system"):
        get_ats_adapter("workday")
