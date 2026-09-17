from uuid import uuid4

from sqlalchemy import Column, Text
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class Location(Base):
    __tablename__ = "location"

    location_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(Text, nullable=False)
    normalized_name = Column(Text, nullable=False, unique=True)
