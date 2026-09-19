from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel


class JobSortField(str, Enum):
    """Sortable columns of the job list. Salary is deliberately absent:
    values mix pay periods, currencies and levels.fyi estimates, so ordering
    them against each other is meaningless (the same reason min_salary and
    max_salary require a salary_period)."""

    POSTED_DATE = "posted_date"
    TITLE = "title"
    COMPANY = "company"


class SortDirection(str, Enum):
    ASC = "asc"
    DESC = "desc"


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
