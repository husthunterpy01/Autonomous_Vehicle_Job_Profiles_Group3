from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.company import CompanyResponse
from app.schemas.job import JobResponse


class FavoriteJobResponse(BaseModel):
    job_id: UUID
    created_at: datetime
    job: JobResponse


class FavoriteCompanyResponse(BaseModel):
    company_id: UUID
    created_at: datetime
    company: CompanyResponse
