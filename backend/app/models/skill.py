from uuid import uuid4

from sqlalchemy import Column, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class Skill(Base):
    __tablename__ = "skill"
    __table_args__ = (UniqueConstraint("normalized_name", "skill_type"),)

    skill_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    skill_name = Column(Text, nullable=False)
    normalized_name = Column(Text, nullable=False)
    skill_type = Column(String(64), nullable=False)
