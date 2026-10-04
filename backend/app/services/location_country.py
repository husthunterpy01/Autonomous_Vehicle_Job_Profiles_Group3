"""Keeps location.country in step with location names (BE-21, #112)."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Location, job_location
from app.utils.location_country import country_for


class LocationCountryService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def assign_country(location: Location) -> bool:
        """Sets a location's country from its name. Returns whether it changed.

        Needs no session, so sync and job creation call it on a new location
        before adding it.
        """
        country = country_for(location.name)
        if location.country == country:
            return False
        location.country = country
        return True

    def refresh(self) -> dict[str, int]:
        """Recomputes every location's country, e.g. after the rules gained a city."""
        locations = self.db.query(Location).all()
        changed = sum(self.assign_country(location) for location in locations)
        self.db.flush()
        return {
            "locations": len(locations),
            "with_country": sum(1 for location in locations if location.country),
            "changed": changed,
        }

    def country_job_counts(self) -> list[dict]:
        """Countries that currently have jobs, most jobs first. A job with
        locations in two countries counts once for each; a job with two
        locations in the same country counts once."""
        job_count = func.count(func.distinct(job_location.c.job_id))
        rows = self.db.execute(
            select(Location.country, job_count.label("job_count"))
            .join(job_location, job_location.c.location_id == Location.location_id)
            .where(Location.country.is_not(None))
            .group_by(Location.country)
            .order_by(job_count.desc(), Location.country)
        ).all()
        return [{"country": row.country, "job_count": row.job_count} for row in rows]
