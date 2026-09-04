from uuid import uuid4

from sqlalchemy import Column, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class Location(Base):
    __tablename__ = "location"

    location_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(Text, nullable=False)
    normalized_name = Column(Text, nullable=False, unique=True)


class JobLocation(Base):
    __tablename__ = "job_location"

    job_id = Column(UUID(as_uuid=True), ForeignKey("jobposting.job_id", ondelete="CASCADE"), primary_key=True)
    location_id = Column(UUID(as_uuid=True), ForeignKey("location.location_id"), primary_key=True)


class Skill(Base):
    __tablename__ = "skill"
    __table_args__ = (UniqueConstraint("normalized_name", "skill_type"),)

    skill_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    skill_name = Column(Text, nullable=False)
    normalized_name = Column(Text, nullable=False)
    skill_type = Column(String(64), nullable=False)


class JobSkill(Base):
    __tablename__ = "job_skill"

    job_id = Column(UUID(as_uuid=True), ForeignKey("jobposting.job_id", ondelete="CASCADE"), primary_key=True)
    skill_id = Column(UUID(as_uuid=True), ForeignKey("skill.skill_id"), primary_key=True)
