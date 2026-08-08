from uuid import uuid4

from sqlalchemy import Boolean, Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class CompanyLocation(Base):
    __tablename__ = "company_location"

    location_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    country = Column(String(255), nullable=False)
    city = Column(String(255), nullable=False)
    is_hq = Column(Boolean, nullable=False, default=False)

    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("company.company_id"),
        nullable=False,
    )

    company = relationship("Company", back_populates="locations")
