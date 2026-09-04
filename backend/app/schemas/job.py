from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class JobResponse(BaseModel):
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
