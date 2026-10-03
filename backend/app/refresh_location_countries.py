"""Manual command: python -m app.refresh_location_countries.

Recomputes location_country for every location. Run it once after
be21_location_country_migration.sql, and again whenever the rules in
app/utils/location_country.py change. New locations get their countries
during sync, so a normal import does not need it.
"""
import argparse

from sqlalchemy.orm import Session

from app.core.database import engine
from app.services.location_country import LocationCountryService
from app.utils.cli import run_command
from scripts.sync_to_supabase import sync_if_configured


def main():
    parser = argparse.ArgumentParser(description="Recompute each location's countries from its name")

    def execute(_args):
        with Session(engine) as db, db.begin():
            return LocationCountryService(db).refresh()

    run_command(parser, execute)
    sync_if_configured()


if __name__ == "__main__":
    main()
