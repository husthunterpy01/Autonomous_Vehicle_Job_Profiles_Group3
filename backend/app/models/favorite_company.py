from sqlalchemy import Column, DateTime, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class FavoriteCompany(Base):
    __tablename__ = "favorite_company"
    __table_args__ = (
        Index("ix_favorite_company_user_created", "user_id", "created_at"),
        Index("ix_favorite_company_company_id", "company_id"),
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("user_account.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("company.company_id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    company = relationship("Company")
