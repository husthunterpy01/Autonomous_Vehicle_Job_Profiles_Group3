"""Manual sync: python -m app.sync_silver --allow-unclassified (development only)."""
import argparse
import os

from sqlalchemy import create_engine

from app.core.database import engine
from app.services.silver_pipeline import SilverPipeline
from app.utils.cli import run_command


def main():
    parser = argparse.ArgumentParser(description="Sync Silver staging rows into backend ERD tables")
    parser.add_argument("--allow-unclassified", action="store_true", help="Allow unclassified staging rows for development only")

    def execute(args):
        if not args.allow_unclassified:
            raise ValueError("AV classification handoff is not integrated yet. Use --allow-unclassified only for development validation.")
        source_url = os.environ.get("SILVER_DATABASE_URL")
        if not source_url:
            raise ValueError("Set SILVER_DATABASE_URL to the database containing silver.cleaned_job_postings")
        source = create_engine(source_url, pool_pre_ping=True)
        try:
            return SilverPipeline(engine).sync(source, allow_unclassified=args.allow_unclassified)
        finally:
            source.dispose()

    run_command(parser, execute)


if __name__ == "__main__":
    main()
