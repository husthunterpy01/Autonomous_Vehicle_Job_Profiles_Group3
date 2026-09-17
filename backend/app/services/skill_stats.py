from app.models.jobposting import job_skill
from app.models.skill import Skill
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.schemas.skill import SkillStatResponse
class SkillService:
    def __init__(self, db: Session):
        self.db = db

    def get_skill_stat_per_job(self)-> list[SkillStatResponse]:
        skill_count_by_job = self.db.query(
            Skill.skill_id,
            Skill.skill_name,
            func.count(job_skill.c.job_id).label('number_of_occurence')
        ) \
        .join(job_skill, Skill.skill_id == job_skill.c.skill_id) \
        .group_by(Skill.skill_id) \
        .all()

        if not skill_count_by_job:
            return []

        return skill_count_by_job

