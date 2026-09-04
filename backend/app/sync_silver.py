"""Manual sync: python -m app.sync_silver --allow-unclassified (development only)."""
import argparse
import json
import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.database import engine
from app.services.silver_sync import SilverSync


def main():
    parser = argparse.ArgumentParser(description="Sync Silver staging rows into backend ERD tables")
    parser.add_argument("--allow-unclassified", action="store_true", help="Explicitly allow staging rows before Harshil's AV gate is integrated; development only")
    args = parser.parse_args()
    if not args.allow_unclassified:
        parser.error("AV classification handoff is not integrated yet. Use --allow-unclassified only for development validation.")
    source_url = os.environ.get("SILVER_DATABASE_URL")
    if not source_url:
        parser.error("Set SILVER_DATABASE_URL to the database containing silver.cleaned_job_postings")
    source = create_engine(source_url, pool_pre_ping=True)
    try:
        with source.connect() as connection, Session(engine) as db, db.begin():
            if engine.dialect.name == "postgresql":
                # Prevent two manual sync processes from racing on natural keys.
                db.execute(text("SELECT pg_advisory_xact_lock(80009001)"))
            records = connection.execution_options(stream_results=True).execute(
                text("SELECT * FROM silver.cleaned_job_postings ORDER BY deduplication_key")
            ).mappings()
            counts = SilverSync(db).run(records)
        print(json.dumps(counts))
    finally:
        source.dispose()


if __name__ == "__main__":
    main()
