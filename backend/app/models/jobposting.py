from uuid import uuid4

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class JobPosting(Base):
    __tablename__ = "jobposting"

    job_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), unique=True, nullable=False)
    title = Column(String(255), nullable=False)
    department = Column(String(255), nullable=False)
    employment_type = Column(Integer, nullable=False)
    job_location = Column(String(255), nullable=False)
    seniority_level = Column(Integer, nullable=False)
    salary_average = Column(Float, nullable=False)
    salary_currency = Column(String(255), nullable=False)
    raw_description = Column(Text, nullable=False)
    posted_date = Column(DateTime, nullable=False)
    source_platform = Column(String(255), nullable=False)
    extraction_confidence = Column(Float, nullable=False)
    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("company.company_id"),
        nullable=False,
    )
