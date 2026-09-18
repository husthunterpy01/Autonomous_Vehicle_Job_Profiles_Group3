from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.job import JobResponse, JobSortField, SalaryPeriod, SortDirection
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
    min_salary: float | None = Query(None, ge=0),
    max_salary: float | None = Query(None, ge=0),
    salary_period: SalaryPeriod | None = None,
    has_salary: bool | None = None,
    sort: JobSortField = JobSortField.POSTED_DATE,
    direction: SortDirection | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
):
    if (min_salary is not None or max_salary is not None) and salary_period is None:
        # salary_min/salary_max are raw numbers with no currency/period
        # normalization - comparing them across periods (a $30/hour rate vs
        # a $150,000/year salary) or across an estimated levels.fyi median
        # vs a real disclosed range is meaningless. Requiring salary_period
        # keeps the comparison inside one consistent bucket instead of
        # silently mixing magnitudes that were never comparable.
        raise HTTPException(
            status_code=422,
            detail="salary_period is required when min_salary or max_salary is set.",
        )
    return job_service.list_jobs(
        db, q=q, location=location, skill=skill, category_id=category_id, company_id=company_id,
        employment_type=employment_type, min_salary=min_salary, max_salary=max_salary,
        salary_period=salary_period.value if salary_period else None,
        has_salary=has_salary, sort=sort, direction=direction, page=page, page_size=page_size,
    )


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: UUID, db: DbSession):
    job = job_service.get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
