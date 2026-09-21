from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.enums.employment_type import EmploymentType
from app.enums.seniority_type import SeniorityLevel


class SalaryPeriod(str, Enum):
    """The single source of truth for valid salary_period values, on both
    the write path (salary_sync.SALARY_PERIODS derives from this) and the
    read path (the /jobs salary_period query param) - previously the query
    param accepted any string, so an off-by-synonym value like "annual"
    (the real stored value is "yearly") silently matched zero rows and
    returned an empty 200 instead of a 422 naming the valid choices."""

    YEARLY = "yearly"
    MONTHLY = "monthly"
    WEEKLY = "weekly"
    DAILY = "daily"
    HOURLY = "hourly"


class SubCategoryResponse(BaseModel):
    category_id: UUID
    sub_type: str


class CategoryResponse(BaseModel):
    """A job gets exactly one main_type (see scrapers/service/llm/
    category_hierarchy.py), so it's mentioned once here with every sub_type
    that shares it listed underneath, instead of repeating main_type on a
    flat list of per-sub_type entries."""

    main_type: str | None
    taxonomy_version: int
    sub_types: list[SubCategoryResponse]


class JobResponse(BaseModel):
    category: CategoryResponse | None = None
    job_id: UUID
    title: str
    company_id: UUID
    company_name: str
    locations: list[str]
    skills: list[str]
    employment_type: int | None
    raw_description: str
    source_url: str | None
    posted_date: datetime | None
    salary_min: float | None
    salary_max: float | None
    salary_average: float | None
    salary_currency: str | None
    salary_period: str | None
    salary_source: str | None


class JobDetailResponse(JobResponse):
    """Full public representation returned for one job."""

    department: str | None
    seniority_level: int | None
    requirements: str | None
    source_platform: str | None
    source_job_id: str | None


class JobCreate(BaseModel):
    """Validated payload for the internal/system job-write endpoint."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "source_key": "waymo-robotics-engineer-123",
                "company_id": "11111111-1111-1111-1111-111111111111",
                "title": "Robotics Software Engineer",
                "description": "Build planning software for autonomous vehicles.",
                "requirements": "Python, C++, and robotics experience.",
                "department": "Engineering",
                "employment_type": 1,
                "seniority_level": 3,
                "source_platform": "Greenhouse",
                "source_job_id": "123",
                "source_url": "https://example.com/jobs/123",
                "posted_date": "2026-09-21T08:00:00Z",
                "salary_min": 140000,
                "salary_max": 180000,
                "salary_currency": "USD",
                "salary_period": "yearly",
                "salary_source": "api",
                "location_ids": [],
                "skill_ids": [],
                "category_ids": [],
            }
        },
    )

    source_key: str = Field(min_length=1, max_length=250)
    company_id: UUID
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    requirements: str | None = None
    department: str | None = Field(default=None, max_length=255)
    employment_type: EmploymentType | None = None
    seniority_level: SeniorityLevel | None = None
    posted_date: datetime | None = None
    source_platform: str | None = Field(default=None, max_length=255)
    source_job_id: str | None = None
    source_url: AnyHttpUrl | None = None
    extraction_confidence: float | None = Field(default=None, ge=0, le=1)
    salary_min: float | None = Field(default=None, gt=0)
    salary_max: float | None = Field(default=None, gt=0)
    salary_average: float | None = Field(default=None, gt=0)
    salary_currency: str | None = Field(default=None, min_length=3, max_length=3)
    salary_period: SalaryPeriod | None = None
    salary_source: str | None = None
    location_ids: list[UUID] = Field(default_factory=list)
    skill_ids: list[UUID] = Field(default_factory=list)
    category_ids: list[UUID] = Field(default_factory=list)

    @field_validator(
        "source_key",
        "title",
        "description",
        "requirements",
        "department",
        "source_platform",
        "source_job_id",
        "salary_source",
    )
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("salary_currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        return value.strip().upper() if isinstance(value, str) else value

    @field_validator(
        "salary_min",
        "salary_max",
        "salary_average",
        "extraction_confidence",
        mode="before",
    )
    @classmethod
    def require_numeric_type(cls, value):
        if value is not None and (
            isinstance(value, bool) or not isinstance(value, (int, float))
        ):
            raise ValueError("must be a number, not a numeric string")
        return value

    @field_validator("location_ids", "skill_ids", "category_ids")
    @classmethod
    def reject_duplicate_ids(cls, values: list[UUID]) -> list[UUID]:
        if len(values) != len(set(values)):
            raise ValueError("must not contain duplicate IDs")
        return values

    @field_validator("posted_date")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_salary(self):
        has_range = self.salary_min is not None or self.salary_max is not None
        has_average = self.salary_average is not None
        metadata = (self.salary_currency, self.salary_period, self.salary_source)

        if has_range and has_average:
            raise ValueError(
                "salary_average and salary_min/salary_max are mutually exclusive"
            )
        if has_range and (self.salary_min is None or self.salary_max is None):
            raise ValueError("salary_min and salary_max must be provided together")
        if has_range and self.salary_min > self.salary_max:
            raise ValueError("salary_max must be greater than or equal to salary_min")
        if has_range or has_average:
            if any(value is None for value in metadata):
                raise ValueError(
                    "salary_currency, salary_period, and salary_source are required "
                    "when salary is provided"
                )
            if self.salary_source not in {"api", "regex", "levels_fyi_average"}:
                raise ValueError(
                    "salary_source must be api, regex, or levels_fyi_average"
                )
        elif any(value is not None for value in metadata):
            raise ValueError("salary metadata requires a salary value")
        return self
