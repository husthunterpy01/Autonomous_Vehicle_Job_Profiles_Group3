from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


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


class CategoryResponse(BaseModel):
    category_id: UUID
    main_type: str | None
    sub_type: str
    taxonomy_version: int


class JobResponse(BaseModel):
    categories: list[CategoryResponse] = Field(default_factory=list)
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
