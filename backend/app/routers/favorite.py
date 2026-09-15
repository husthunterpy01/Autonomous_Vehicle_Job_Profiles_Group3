from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.job import JobResponse
from app.services import favorite as favorite_service

router = APIRouter(prefix="/favorites", tags=["favorites"])
DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("", response_model=list[JobResponse])
def list_favorites(db: DbSession, current_user: CurrentUser):
    return favorite_service.list_favorites(db, current_user.user_id)


@router.post("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def add_favorite(job_id: UUID, db: DbSession, current_user: CurrentUser):
    favorite_service.add_favorite(db, current_user.user_id, job_id)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_favorite(job_id: UUID, db: DbSession, current_user: CurrentUser):
    favorite_service.remove_favorite(db, current_user.user_id, job_id)
