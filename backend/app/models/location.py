from uuid import uuid4

from sqlalchemy import Column, Index, Text
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class Location(Base):
    __tablename__ = "location"
    __table_args__ = (Index("ix_location_country", "country"),)

    location_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(Text, nullable=False)
    normalized_name = Column(Text, nullable=False, unique=True)

    # The one country the name refers to, derived by app/utils/location_country.py.
    # None when the name names no country ("Remote") or several ("Remote US & Canada").
    country = Column(Text, nullable=True)
