from uuid import uuid4

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class JobPosting(Base):
    __tablename__ = "jobposting"
    # Mirrors app/sql/be13_salary_constraints_migration.sql so salary rules hold
    # for any writer, not only app/services/salary_sync.py.
    __table_args__ = (
        CheckConstraint("salary_min IS NULL OR salary_min > 0", name="ck_jobposting_salary_min_positive"),
        CheckConstraint("salary_max IS NULL OR salary_max > 0", name="ck_jobposting_salary_max_positive"),
        CheckConstraint("salary_average IS NULL OR salary_average > 0", name="ck_jobposting_salary_average_positive"),
        CheckConstraint(
            "salary_min IS NULL OR salary_max IS NULL OR salary_min <= salary_max",
            name="ck_jobposting_salary_range_order",
        ),
        # A job has a published range or a levels.fyi estimate, never both.
        CheckConstraint(
            "salary_average IS NULL OR (salary_min IS NULL AND salary_max IS NULL)",
            name="ck_jobposting_salary_range_or_average",
        ),
        # Any salary needs its currency, pay period and source to be comparable.
        CheckConstraint(
            "(salary_min IS NULL AND salary_max IS NULL AND salary_average IS NULL)"
            " OR (salary_currency IS NOT NULL AND salary_period IS NOT NULL AND salary_source IS NOT NULL)",
            name="ck_jobposting_salary_details_required",
        ),
    )

    job_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), unique=True, nullable=False)
    title = Column(String(255), nullable=False)
    department = Column(String(255), nullable=True)
    employment_type = Column(Integer, nullable=True)
    seniority_level = Column(Integer, nullable=True)
    salary_average = Column(Float, nullable=True)
    salary_currency = Column(String(255), nullable=True)
    salary_min = Column(Float, nullable=True)
    salary_max = Column(Float, nullable=True)
    salary_period = Column(String(255), nullable=True)
    salary_source = Column(String(255), nullable=True)
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
