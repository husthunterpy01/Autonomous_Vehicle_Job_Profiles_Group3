from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.company import Company
from app.schemas.company import CompanyCreate, CompanyResponse
from app.services.company import CompanyService

router = APIRouter(prefix="/companies", tags=["companies"])


def to_company_response(company: Company) -> CompanyResponse:
    return CompanyResponse(
        company_id=company.company_id,
        name=company.name,
        website_url=company.website_url,
        career_page_url=company.career_page_url,
        company_type=company.company_type,
        datasource_status=company.datasource_status,
    )


@router.get("", response_model=list[CompanyResponse])
def list_companies(db: Session = Depends(get_db)):
    return [to_company_response(company) for company in CompanyService.get_companies(db)]


@router.get("/{company_id}", response_model=CompanyResponse)
def get_company(company_id: UUID, db: Session = Depends(get_db)):
    return to_company_response(CompanyService.get_company_by_id(db, company_id))


@router.post("", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
def create_company(
    data: CompanyCreate,
    db: Session = Depends(get_db),
):
    return to_company_response(CompanyService.add_new_company(db, data))
