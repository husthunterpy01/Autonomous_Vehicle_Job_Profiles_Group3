
from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class JobSkill(Base):
    __tablename__ = "job_skill"

    job_id = Column(UUID(as_uuid=True), ForeignKey("jobposting.job_id", ondelete="CASCADE"), primary_key=True)
    skill_id = Column(UUID(as_uuid=True), ForeignKey("skill.skill_id"), primary_key=True)
