from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.jobposting import JobPosting, job_category
from app.schemas.category import CategoryStatResponse


class CategoryService:
    def __init__(self, db: Session):
        self.db = db

    def get_category_stat_per_job(self) -> list[CategoryStatResponse]:
        rows = (
            self.db.query(
                Category.category_id,
                Category.sub_type,
                Category.main_type,
                func.count(job_category.c.job_id).label("job_count"),
            )
            .join(job_category, job_category.c.category_id == Category.category_id)
            .join(JobPosting, JobPosting.job_id == job_category.c.job_id)
            .filter(JobPosting.is_av_relevant.is_(True))
            .group_by(Category.category_id)
            .order_by(func.count(job_category.c.job_id).desc())
            .all()
        )
        return [
            CategoryStatResponse(category_id=category_id, sub_type=sub_type, main_type=main_type, job_count=job_count)
            for category_id, sub_type, main_type, job_count in rows
        ]
