from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Favorite, JobPosting
from app.schemas.job import JobResponse
from app.services.job import job_query, to_response


def list_favorites(db: Session, user_id: UUID) -> list[JobResponse]:
    jobs = (
        job_query(db)
        .join(Favorite, Favorite.job_id == JobPosting.job_id)
        .filter(Favorite.user_id == user_id)
        .order_by(Favorite.created_at.desc())
        .all()
    )
    return [to_response(job) for job in jobs]


def add_favorite(db: Session, user_id: UUID, job_id: UUID) -> None:
    job_exists = (
        db.query(JobPosting.job_id).filter(JobPosting.job_id == job_id).first()
    )
    if job_exists is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
        )

    if db.get(Favorite, (user_id, job_id)) is None:
        db.add(Favorite(user_id=user_id, job_id=job_id))
        db.commit()


def remove_favorite(db: Session, user_id: UUID, job_id: UUID) -> None:
    favorite = db.get(Favorite, (user_id, job_id))
    if favorite is not None:
        db.delete(favorite)
        db.commit()
