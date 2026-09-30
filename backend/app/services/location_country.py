"""Keeps location_country in step with location names (BE-21, #112)."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import Location, LocationCountry, job_location
from app.utils.location_country import countries_for


def assign_countries(location: Location) -> bool:
    """Sets a location's countries from its name. Returns whether they changed."""
    wanted = countries_for(location.name)
    current = {row.country for row in location.countries}
    if current == wanted:
        return False
    location.countries = [row for row in location.countries if row.country in wanted] + [
        LocationCountry(country=country) for country in sorted(wanted - current)
    ]
    return True


def refresh_location_countries(db: Session) -> dict[str, int]:
    """Recomputes every location's countries, e.g. after the rules gained a city."""
    locations = db.query(Location).options(selectinload(Location.countries)).all()
    changed = sum(assign_countries(location) for location in locations)
    db.flush()
    return {
        "locations": len(locations),
        "with_country": sum(1 for location in locations if location.countries),
        "changed": changed,
    }


def country_job_counts(db: Session) -> list[dict]:
    """Countries that currently have jobs, most jobs first. A job in two
    countries counts once for each; a job with two locations in the same
    country counts once."""
    job_count = func.count(func.distinct(job_location.c.job_id))
    rows = db.execute(
        select(LocationCountry.country, job_count.label("job_count"))
        .join(job_location, job_location.c.location_id == LocationCountry.location_id)
        .group_by(LocationCountry.country)
        .order_by(job_count.desc(), LocationCountry.country)
    ).all()
    return [{"country": row.country, "job_count": row.job_count} for row in rows]
