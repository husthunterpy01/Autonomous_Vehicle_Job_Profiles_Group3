import pytest

from scrapers.strategy.ats.ashbystrategy import AshbyStrategy
from scrapers.strategy.ats.greenhousestrategy import GreenhouseStrategy
from scrapers.strategy.ats.leverstrategy import LeverStrategy
from scrapers.strategy.ats.smartrecruiter import SmartRecruiterStrategy
from scrapers.strategy.registry import get_ats_adapter


def test_greenhouse_maps_jobs_to_bronze_payload():
    jobs = GreenhouseStrategy("greenhouse").map_response_to_bronze_payload(
        "Stack AV",
        "US",
        {
            "jobs": [
                {
                    "title": "Engineer",
                    "content": "<p>Build autonomy software</p>",
                    "location": {"name": "Pittsburgh, PA"},
                    "first_published": "2026-01-01T00:00:00Z",
                    "absolute_url": "https://boards.greenhouse.io/stackav/jobs/1",
                }
            ]
        },
    )

    assert len(jobs) == 1
    assert jobs[0].ats_name == "greenhouse"
    assert jobs[0].company_name == "Stack AV"
    assert jobs[0].job_name == "Engineer"
    assert jobs[0].job_description == "<p>Build autonomy software</p>"
    assert jobs[0].location == "Pittsburgh, PA"
    assert jobs[0].job_url.endswith("/jobs/1")
    assert jobs[0].employment_type is None


def test_ashby_maps_jobs_and_secondary_locations():
    jobs = AshbyStrategy("ashby").map_response_to_bronze_payload(
        "42dot",
        "KR",
        {
            "jobs": [
                {
                    "title": "Software Engineer",
                    "descriptionPlain": "Work on autonomy.",
                    "location": "Seoul",
                    "secondaryLocations": [{"location": "Palo Alto"}],
                    "publishedAt": "2026-02-01T00:00:00Z",
                    "jobUrl": "https://jobs.ashbyhq.com/42dot/abc",
                    "employmentType": "Full-time",
                }
            ]
        },
    )

    assert jobs[0].job_name == "Software Engineer"
    assert jobs[0].location == "Seoul | Palo Alto"
    assert jobs[0].employment_type == "Full-time"


def test_lever_maps_list_payload():
    jobs = LeverStrategy("lever").map_response_to_bronze_payload(
        "Waabi",
        "CA",
        [
            {
                "text": "Research Engineer",
                "descriptionPlain": "Research autonomy.",
                "categories": {"location": "Toronto", "commitment": "Full-time"},
                "createdAt": 1700000000000,
                "hostedUrl": "https://jobs.lever.co/waabi/abc",
                "workplaceType": "hybrid",
            }
        ],
    )

    assert jobs[0].job_name == "Research Engineer"
    assert jobs[0].location == "Toronto"
    assert jobs[0].employment_type == "Full-time"


def test_lever_maps_contract_commitment_not_workplace_type():
    jobs = LeverStrategy("lever").map_response_to_bronze_payload(
        "WeRide",
        "US",
        [
            {
                "text": "Contract Vehicle Operations Specialist (Bilingual Spanish)",
                "descriptionPlain": "Operate test vehicles.",
                "categories": {
                    "location": "San Jose, CA",
                    "commitment": "Contract",
                },
                "createdAt": 1783379901263,
                "hostedUrl": "https://jobs.lever.co/weride/67194770-ca27-4291-82ac-a90e58967e29",
                "workplaceType": "onsite",
            }
        ],
    )

    assert jobs[0].employment_type == "Contract"


def test_lever_employment_type_none_when_commitment_missing():
    jobs = LeverStrategy("lever").map_response_to_bronze_payload(
        "Waabi",
        "CA",
        [
            {
                "text": "Engineer",
                "descriptionPlain": "Build the driver.",
                "categories": {"location": "Toronto"},
                "createdAt": 1690000000000,
                "hostedUrl": "https://jobs.lever.co/waabi/abc",
                "workplaceType": "hybrid",
            }
        ],
    )

    assert jobs[0].employment_type is None


def test_smartrecruiters_maps_job_ad_sections():
    jobs = SmartRecruiterStrategy("smartrecruiters").map_response_to_bronze_payload(
        "Bosch",
        "DE",
        {
            "content": [
                {
                    "name": "Product Data Operator - Temporary",
                    "postingUrl": "https://jobs.smartrecruiters.com/BoschGroup/744000146470121-product-data-operator-temporary",
                    "location": {"fullLocation": "Beograd, , Serbia"},
                    "releasedDate": "2026-08-31T13:38:57.052Z",
                    "typeOfEmployment": {"label": "Full-time"},
                    "jobAd": {
                        "sections": {
                            "jobDescription": {"text": "<p>Release product documents</p>"},
                            "qualifications": {"text": "<p>SAP knowledge</p>"},
                        }
                    },
                }
            ]
        },
    )

    assert jobs[0].job_name == "Product Data Operator - Temporary"
    assert jobs[0].job_description == "<p>Release product documents</p>\n<p>SAP knowledge</p>"
    assert jobs[0].job_url.endswith("product-data-operator-temporary")
    assert jobs[0].employment_type == "Full-time"


def test_smartrecruiters_employment_type_none_when_label_missing():
    jobs = SmartRecruiterStrategy("smartrecruiters").map_response_to_bronze_payload(
        "Bosch",
        "DE",
        {
            "content": [
                {
                    "name": "Operator",
                    "postingUrl": "https://jobs.smartrecruiters.com/BoschGroup/1",
                    "location": {"fullLocation": "Beograd, , Serbia"},
                    "releasedDate": "2026-08-31T13:38:57.052Z",
                    "jobAd": {"sections": {"jobDescription": {"text": "<p>Work</p>"}}},
                }
            ]
        },
    )

    assert jobs[0].employment_type is None


def test_get_ats_adapter_returns_registered_strategy():
    adapter = get_ats_adapter("greenhouse")

    assert isinstance(adapter, GreenhouseStrategy)
    assert adapter.source_system == "greenhouse"


def test_unknown_source_system_raises():
    with pytest.raises(ValueError, match="Unknown source system"):
        get_ats_adapter("workday")
