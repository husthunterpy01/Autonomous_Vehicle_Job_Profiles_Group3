
from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class JobLocation(Base):
    __tablename__ = "job_location"

    job_id = Column(UUID(as_uuid=True), ForeignKey("jobposting.job_id", ondelete="CASCADE"), primary_key=True)
    location_id = Column(UUID(as_uuid=True), ForeignKey("location.location_id"), primary_key=True)
