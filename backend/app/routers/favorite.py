from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.favorite import FavoriteCompanyResponse, FavoriteJobResponse
from app.services.favorite import (
    FavoriteAlreadyExists,
    FavoriteNotFound,
    FavoriteService,
    FavoriteTargetNotFound,
)

router = APIRouter(prefix="/favorites", tags=["favorites"])
DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("/jobs", response_model=list[FavoriteJobResponse])
def list_favorite_jobs(db: DbSession, current_user: CurrentUser):
    return FavoriteService.list_jobs(db, current_user.user_id)


@router.post(
    "/jobs/{job_id}",
    response_model=FavoriteJobResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_favorite_job(job_id: UUID, db: DbSession, current_user: CurrentUser):
    try:
        return FavoriteService.add_job(db, current_user.user_id, job_id)
    except FavoriteTargetNotFound as error:
        raise HTTPException(status_code=404, detail="Job not found") from error
    except FavoriteAlreadyExists as error:
        raise HTTPException(status_code=409, detail="Job already favorited") from error


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_favorite_job(job_id: UUID, db: DbSession, current_user: CurrentUser):
    try:
        FavoriteService.remove_job(db, current_user.user_id, job_id)
    except FavoriteNotFound as error:
        raise HTTPException(status_code=404, detail="Favorite job not found") from error


@router.get("/companies", response_model=list[FavoriteCompanyResponse])
def list_favorite_companies(db: DbSession, current_user: CurrentUser):
    return FavoriteService.list_companies(db, current_user.user_id)


@router.post(
    "/companies/{company_id}",
    response_model=FavoriteCompanyResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_favorite_company(company_id: UUID, db: DbSession, current_user: CurrentUser):
    try:
        return FavoriteService.add_company(db, current_user.user_id, company_id)
    except FavoriteTargetNotFound as error:
        raise HTTPException(status_code=404, detail="Company not found") from error
    except FavoriteAlreadyExists as error:
        raise HTTPException(status_code=409, detail="Company already favorited") from error


@router.delete("/companies/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_favorite_company(company_id: UUID, db: DbSession, current_user: CurrentUser):
    try:
        FavoriteService.remove_company(db, current_user.user_id, company_id)
    except FavoriteNotFound as error:
        raise HTTPException(status_code=404, detail="Favorite company not found") from error
