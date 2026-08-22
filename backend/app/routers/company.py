from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.company import (
    CompanyCreate,
    CompanyResponse,
    CompanyWithJobNumberResponse,
)
from app.services.company import CompanyService
from app.utils.pagination import PageResponse

router = APIRouter(prefix="/companies", tags=["company"])

DbSession = Annotated[Session, Depends(get_db)]
PaginationParams = Annotated[dict[str, int], Depends(PageResponse.pagination_params)]


@router.get("", response_model=list[CompanyResponse])
def get_companies(db: DbSession):
    companies = CompanyService.get_companies(db)
    responses = []
    for company in companies:
        responses.append(CompanyService.to_response(company))
    return responses


@router.get("/with-job-counts", response_model=PageResponse[CompanyWithJobNumberResponse])
def get_companies_with_job_numbers(
    db: DbSession,
    pagination: PaginationParams,
):
    return CompanyService.get_companies_with_num_jobs(db, **pagination)


@router.get("/{company_id}", response_model=CompanyResponse)
def get_company_by_id(company_id: UUID, db: DbSession):
    company = CompanyService.get_company_by_id(db, company_id)
    return CompanyService.to_response(company)


@router.post("", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
def create_company(data: CompanyCreate, db: DbSession):
    company = CompanyService.add_new_company(db, data)
    return CompanyService.to_response(company)
