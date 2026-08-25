from uuid import uuid4

from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class Company(Base):
    __tablename__ = "company"

    company_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), unique=True, nullable=False)
    company_type = Column(String(255), nullable=False)
    website_url = Column(String(255), unique=True, nullable=False)
    career_page_url = Column(String(255), unique=True, nullable=False)
    datasource_status = Column(String(255), nullable=False)

    locations = relationship(
        "CompanyLocation",
        back_populates="company",
        cascade="all, delete-orphan",
    )
