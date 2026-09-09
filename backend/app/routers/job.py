from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.job import JobResponse
from app.services import job as job_service
from app.utils.pagination import PageResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=PageResponse[JobResponse])
def list_jobs(
    db: DbSession,
    q: str | None = None,
    location: str | None = None,
    skill: str | None = None,
    category_id: UUID | None = None,
    company_id: UUID | None = None,
    employment_type: int | None = Query(None, ge=1, le=6),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
):
    return job_service.list_jobs(db, q=q, location=location, skill=skill, category_id=category_id, company_id=company_id, employment_type=employment_type, page=page, page_size=page_size)


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: UUID, db: DbSession):
    job = job_service.get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
