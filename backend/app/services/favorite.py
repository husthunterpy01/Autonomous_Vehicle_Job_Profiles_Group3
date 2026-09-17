from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models import Company, FavoriteCompany, FavoriteJob, JobPosting
from app.schemas.favorite import FavoriteCompanyResponse, FavoriteJobResponse
from app.services.company import CompanyService
from app.services.job import to_response as job_to_response


class FavoriteAlreadyExists(Exception):
    pass


class FavoriteNotFound(Exception):
    pass


class FavoriteTargetNotFound(Exception):
    pass


class FavoriteService:
    @staticmethod
    def _add(
        db: Session,
        user_id: UUID,
        target_id: UUID,
        target_model,
        favorite_model,
        target_field: str,
    ):
        if db.get(target_model, target_id) is None:
            raise FavoriteTargetNotFound
        if db.get(favorite_model, (user_id, target_id)) is not None:
            raise FavoriteAlreadyExists

        favorite = favorite_model(user_id=user_id, **{target_field: target_id})
        db.add(favorite)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            # A concurrent request can add the same favorite or remove its target
            # after our initial checks. Recheck before assigning an API error.
            if db.get(target_model, target_id) is None:
                raise FavoriteTargetNotFound
            if db.get(favorite_model, (user_id, target_id)) is not None:
                raise FavoriteAlreadyExists
            raise
        db.refresh(favorite)
        return favorite

    @staticmethod
    def _remove(db: Session, user_id: UUID, target_id: UUID, favorite_model) -> None:
        favorite = db.get(favorite_model, (user_id, target_id))
        if favorite is None:
            raise FavoriteNotFound
        db.delete(favorite)
        db.commit()

    @staticmethod
    def _job_response(favorite: FavoriteJob) -> FavoriteJobResponse:
        return FavoriteJobResponse(
            job_id=favorite.job_id,
            created_at=favorite.created_at,
            job=job_to_response(favorite.job),
        )

    @staticmethod
    def _company_response(favorite: FavoriteCompany) -> FavoriteCompanyResponse:
        return FavoriteCompanyResponse(
            company_id=favorite.company_id,
            created_at=favorite.created_at,
            company=CompanyService.to_response(favorite.company),
        )

    @classmethod
    def add_job(cls, db: Session, user_id: UUID, job_id: UUID) -> FavoriteJobResponse:
        favorite = cls._add(db, user_id, job_id, JobPosting, FavoriteJob, "job_id")
        return cls._job_response(favorite)

    @classmethod
    def remove_job(cls, db: Session, user_id: UUID, job_id: UUID) -> None:
        cls._remove(db, user_id, job_id, FavoriteJob)

    @classmethod
    def list_jobs(cls, db: Session, user_id: UUID) -> list[FavoriteJobResponse]:
        favorites = (
            db.query(FavoriteJob)
            .join(FavoriteJob.job)
            .options(
                selectinload(FavoriteJob.job).selectinload(JobPosting.company),
                selectinload(FavoriteJob.job).selectinload(JobPosting.locations),
                selectinload(FavoriteJob.job).selectinload(JobPosting.skills),
                selectinload(FavoriteJob.job).selectinload(JobPosting.categories),
            )
            .filter(FavoriteJob.user_id == user_id)
            .order_by(FavoriteJob.created_at.desc(), FavoriteJob.job_id)
            .all()
        )
        return [cls._job_response(favorite) for favorite in favorites]

    @classmethod
    def add_company(
        cls, db: Session, user_id: UUID, company_id: UUID
    ) -> FavoriteCompanyResponse:
        favorite = cls._add(
            db, user_id, company_id, Company, FavoriteCompany, "company_id"
        )
        return cls._company_response(favorite)

    @classmethod
    def remove_company(cls, db: Session, user_id: UUID, company_id: UUID) -> None:
        cls._remove(db, user_id, company_id, FavoriteCompany)

    @classmethod
    def list_companies(cls, db: Session, user_id: UUID) -> list[FavoriteCompanyResponse]:
        favorites = (
            db.query(FavoriteCompany)
            .join(FavoriteCompany.company)
            .options(selectinload(FavoriteCompany.company))
            .filter(FavoriteCompany.user_id == user_id)
            .order_by(FavoriteCompany.created_at.desc(), FavoriteCompany.company_id)
            .all()
        )
        return [cls._company_response(favorite) for favorite in favorites]
