from uuid import uuid4

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class JobPosting(Base):
    __tablename__ = "jobposting"

    job_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), unique=True, nullable=False)
    title = Column(String(255), nullable=False)
    department = Column(String(255), nullable=True)
    employment_type = Column(Integer, nullable=True)
    job_location = Column(Text, nullable=True)
    seniority_level = Column(Integer, nullable=True)
    salary_average = Column(Float, nullable=True)
    salary_currency = Column(String(255), nullable=True)
    raw_description = Column(Text, nullable=False)
    posted_date = Column(DateTime(timezone=True), nullable=True)
    source_platform = Column(String(255), nullable=True)
    extraction_confidence = Column(Float, nullable=True)
    source_key = Column(Text, unique=True, nullable=True)
    source_job_id = Column(Text, nullable=True)
    bronze_id = Column(Text, nullable=True)
    source_url = Column(Text, nullable=True)
    ingested_at = Column(DateTime(timezone=True), nullable=True)
    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("company.company_id"),
        nullable=False,
    )
    company = relationship("Company")
    locations = relationship("Location", secondary="job_location")
    skills = relationship("Skill", secondary="job_skill")
    categories = relationship("Category", secondary="job_category")
