from sqlalchemy import Column, DateTime, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class FavoriteJob(Base):
    __tablename__ = "favorite_job"
    __table_args__ = (
        Index("ix_favorite_job_user_created", "user_id", "created_at"),
        Index("ix_favorite_job_job_id", "job_id"),
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("user_account.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("jobposting.job_id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    job = relationship("JobPosting")
