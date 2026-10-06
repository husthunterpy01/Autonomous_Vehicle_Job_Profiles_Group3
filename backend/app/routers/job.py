from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.job_write import require_job_write_key
from app.enums.job_sort_field import JobSortField
from app.enums.seniority_type import SeniorityLevel
from app.enums.sort_direction import SortDirection
from app.schemas.job import (
    CountryJobCountResponse,
    JobCreate,
    JobDetailResponse,
    JobResponse,
    SalaryPeriod,
)
from app.services import job as job_service
from app.services.location_country import LocationCountryService
from app.utils.location_country import KNOWN_COUNTRIES, canonical_country
from app.utils.pagination import PageResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])
DbSession = Annotated[Session, Depends(get_db)]


@router.post(
    "",
    response_model=JobDetailResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Related categories are inconsistent"},
        401: {"description": "Missing or invalid job-write key"},
        404: {"description": "Company or related entity does not exist"},
        409: {"description": "A job with this source key already exists"},
        422: {"description": "Request fields failed schema validation"},
        500: {"description": "The job could not be created"},
        503: {"description": "Job writes are not configured"},
    },
)
def create_job(
    data: JobCreate,
    db: DbSession,
    _write_access: Annotated[None, Depends(require_job_write_key)],
):
    try:
        return job_service.create_job(db, data)
    except job_service.InvalidJobDataError as exc:
        raise HTTPException(status_code=400, detail=exc.detail) from exc
    except job_service.JobEntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.detail) from exc
    except job_service.DuplicateJobError as exc:
        raise HTTPException(status_code=409, detail=exc.detail) from exc
    except job_service.JobPersistenceError as exc:
        raise HTTPException(status_code=500, detail=exc.detail) from exc


@router.get(
    "",
    response_model=PageResponse[JobResponse],
    responses={
        400: {"description": "Unknown country, or salary_min greater than salary_max"},
    },
)
def list_jobs(
    db: DbSession,
    q: str | None = None,
    location: str | None = None,
    country: str | None = Query(
        None,
        description=(
            "Only jobs with a location in this country (case-insensitive). "
            "GET /jobs/countries lists the countries that have jobs. Accepted values: "
            + ", ".join(KNOWN_COUNTRIES)
        ),
    ),
    skill: str | None = None,
    category_id: UUID | None = None,
    company_id: UUID | None = None,
    employment_type: int | None = Query(None, ge=1, le=6),
    seniority_level: SeniorityLevel | None = Query(
        None, description="1 junior, 2 mid, 3 senior, 4 principal, 5 lead, 6 manager, 7 director, 8 ceo, 9 other."
    ),
    salary_min: float | None = Query(
        None, ge=0, description="Annual USD equivalent - converted/annualized server-side (BE-22)."
    ),
    salary_max: float | None = Query(
        None, ge=0, description="Annual USD equivalent - converted/annualized server-side (BE-22)."
    ),
    salary_period: SalaryPeriod | None = None,
    has_salary: bool | None = None,
    salary_disclosed: bool | None = None,
    sort: JobSortField = JobSortField.POSTED_DATE,
    direction: SortDirection | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
):
    if salary_min is not None and salary_max is not None and salary_min > salary_max:
        raise HTTPException(
            status_code=400,
            detail="salary_min must not be greater than salary_max.",
        )
    country_name = None
    if country and country.strip():
        country_name = canonical_country(country)
        if country_name is None:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown country '{country.strip()}'. Use a full country name such as 'United States'.",
            )
    return job_service.list_jobs(
        db, q=q, location=location, country=country_name, skill=skill, category_id=category_id, company_id=company_id,
        employment_type=employment_type, seniority_level=seniority_level, salary_min=salary_min, salary_max=salary_max,
        salary_period=salary_period.value if salary_period else None,
        has_salary=has_salary, salary_disclosed=salary_disclosed, sort=sort, direction=direction, page=page, page_size=page_size,
    )


# Declared before /{job_id}, which would otherwise try to read "countries" as a job id.
@router.get("/countries", response_model=list[CountryJobCountResponse])
def list_countries(db: DbSession):
    """Countries that currently have jobs, with their job counts, for the country filter."""
    return LocationCountryService(db).country_job_counts()


@router.get("/{job_id}", response_model=JobDetailResponse)
def get_job(job_id: UUID, db: DbSession):
    job = job_service.get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
