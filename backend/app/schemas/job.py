from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


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
