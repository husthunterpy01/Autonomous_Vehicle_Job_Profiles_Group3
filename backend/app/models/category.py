from uuid import uuid4

from sqlalchemy import (
    CheckConstraint,
    Column,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class Category(Base):
    __tablename__ = "category"
    __table_args__ = (
        UniqueConstraint("taxonomy_version", "normalized_name"),
        CheckConstraint("taxonomy_version > 0"),
    )

    category_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    main_type = Column(Text, nullable=True)
    sub_type = Column(Text, nullable=False)
    normalized_name = Column(Text, nullable=False)
    taxonomy_version = Column(Integer, nullable=False)
