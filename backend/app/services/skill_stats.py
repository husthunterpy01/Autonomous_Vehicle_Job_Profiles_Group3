from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.jobposting import JobPosting, job_skill
from app.models.skill import Skill
from app.schemas.skill import SkillStatResponse


class SkillService:
    def __init__(self, db: Session):
        self.db = db

    def get_skill_stat_per_job(self, limit: int | None = None) -> list[SkillStatResponse]:
        query = (
            self.db.query(
                Skill.skill_id,
                Skill.skill_name,
                func.count(job_skill.c.job_id).label("number_of_occurrences"),
            )
            .join(job_skill, Skill.skill_id == job_skill.c.skill_id)
            .join(JobPosting, JobPosting.job_id == job_skill.c.job_id)
            .filter(JobPosting.is_av_relevant.is_(True))
            .group_by(Skill.skill_id)
            .order_by(func.count(job_skill.c.job_id).desc())
        )
        if limit is not None:
            query = query.limit(limit)
        return query.all()
