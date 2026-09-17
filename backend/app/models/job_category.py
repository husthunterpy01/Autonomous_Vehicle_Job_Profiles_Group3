from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class JobCategory(Base):
    __tablename__ = "job_category"

    job_id = Column(UUID(as_uuid=True), ForeignKey("jobposting.job_id", ondelete="CASCADE"), primary_key=True)
    category_id = Column(UUID(as_uuid=True), ForeignKey("category.category_id"), primary_key=True)
