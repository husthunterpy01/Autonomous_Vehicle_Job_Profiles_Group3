from sqlalchemy import Column, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class LocationCountry(Base):
    """One country a location label names, derived by app/utils/location_country.py."""

    __tablename__ = "location_country"
    __table_args__ = (Index("ix_location_country_country", "country"),)

    location_id = Column(
        UUID(as_uuid=True), ForeignKey("location.location_id", ondelete="CASCADE"), primary_key=True
    )
    country = Column(Text, primary_key=True)
