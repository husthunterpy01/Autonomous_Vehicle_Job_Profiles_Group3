from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.job import JobCreate


def valid_payload():
    return {
        "source_key": "external-123",
        "company_id": uuid4(),
        "title": "AV Software Engineer",
        "description": "Build autonomous driving software.",
    }


def test_job_create_normalizes_values_and_accepts_valid_salary_range():
    job = JobCreate.model_validate(
        {
            **valid_payload(),
            "title": "  AV Software Engineer  ",
            "posted_date": "2026-09-21T08:00:00Z",
            "salary_min": 120000,
            "salary_max": 160000,
            "salary_currency": "usd",
            "salary_period": "yearly",
            "salary_source": "api",
        }
    )

    assert job.title == "AV Software Engineer"
    assert job.salary_currency == "USD"
    assert job.posted_date.utcoffset().total_seconds() == 0


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"salary_min": "120000"}, "must be a number"),
        (
            {"salary_min": 150000, "salary_max": 120000},
            "greater than or equal",
        ),
        ({"salary_average": 140000}, "salary_currency"),
        ({"salary_currency": "USD"}, "salary metadata requires"),
        ({"posted_date": "2026-09-21T08:00:00"}, "timezone"),
    ],
)
def test_job_create_rejects_invalid_types_and_inconsistent_values(changes, message):
    with pytest.raises(ValidationError, match=message):
        JobCreate.model_validate({**valid_payload(), **changes})


def test_job_create_rejects_duplicate_relation_ids():
    location_id = uuid4()
    with pytest.raises(ValidationError, match="duplicate IDs"):
        JobCreate.model_validate(
            {**valid_payload(), "location_ids": [location_id, location_id]}
        )


def test_job_create_rejects_duplicate_nested_relations():
    with pytest.raises(ValidationError, match="skills must not contain duplicates"):
        JobCreate.model_validate(
            {
                **valid_payload(),
                "skills": [
                    {"name": "Python", "skill_type": "programming_language"},
                    {"name": " python ", "skill_type": "programming_language"},
                ],
            }
        )
