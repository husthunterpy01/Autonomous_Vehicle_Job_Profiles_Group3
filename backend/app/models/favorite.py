from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class Favorite(Base):
    __tablename__ = "favorite"

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
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
