import logging
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.company import Company
from app.schemas.company import CompanyCreate, CompanyResponse

logger = logging.getLogger(__name__)

PG_UNIQUE_VIOLATION = "23505"


class CompanyService:
    @classmethod
    def to_response(cls, company: Company) -> CompanyResponse:
        return CompanyResponse(
            company_id=company.company_id,
            name=company.name,
            website_url=company.website_url,
            career_page_url=company.career_page_url,
            company_type=company.company_type,
            datasource_status=company.datasource_status,
        )

    @classmethod
    def get_companies(cls, db: Session) -> list[Company]:
        return db.query(Company).order_by(Company.name.asc()).all()

    @classmethod
    def get_company_by_id(cls, db: Session, company_id: UUID) -> Company:
        company = db.query(Company).filter(Company.company_id == company_id).first()
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company not found: {company_id}",
            )
        return company

    @classmethod
    def add_new_company(cls, db: Session, data: CompanyCreate) -> Company:
        try:
            existing_by_name = (
                db.query(Company).filter(Company.name == data.name).first()
            )
            if existing_by_name:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Company already exists with name: {data.name}",
                )

            existing_by_website = (
                db.query(Company)
                .filter(Company.website_url == data.website_url)
                .first()
            )
            if existing_by_website:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Company already exists with website_url: {data.website_url}",
                )

            existing_by_career_page = (
                db.query(Company)
                .filter(Company.career_page_url == data.career_page_url)
                .first()
            )
            if existing_by_career_page:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Company already exists with career_page_url: "
                        f"{data.career_page_url}"
                    ),
                )

            logger.info("Creating new company=%s", data.name)
            company = Company(
                company_id=uuid4(),
                name=data.name,
                website_url=data.website_url,
                career_page_url=data.career_page_url,
                company_type=data.company_type,
                datasource_status=data.datasource_status,
            )
            db.add(company)
            db.commit()
            db.refresh(company)
            return company
        except HTTPException:
            raise
        except IntegrityError as exc:
            db.rollback()
            logger.exception(
                "Integrity error creating company=%s",
                data.name,
            )
            pgcode = getattr(getattr(exc, "orig", None), "pgcode", None)
            if pgcode == PG_UNIQUE_VIOLATION:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Company already exists "
                        "(name, website_url, or career_page_url must be unique)"
                    ),
                ) from exc
            raise
        except Exception:
            db.rollback()
            logger.exception(
                "Error creating new company=%s",
                data.name,
            )
            raise
