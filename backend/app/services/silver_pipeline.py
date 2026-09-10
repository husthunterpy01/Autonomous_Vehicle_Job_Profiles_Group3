"""Manual Silver pipeline: sync jobs -> validate handoff -> import categories.

Commands delegate database lifecycle and transaction boundaries here.
Source and destination engines remain caller-owned.
"""
from contextlib import contextmanager

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.category_sync import import_categories
from app.services.handoff import validate_records
from app.services.silver_sync import SilverSync


class SilverPipeline:
    def __init__(self, destination):
        self.destination = destination

    @contextmanager
    def _writer(self):
        with Session(self.destination) as db, db.begin():
            if self.destination.dialect.name == "postgresql":
                db.execute(text("SELECT pg_advisory_xact_lock(80009001)"))
            yield db

    def sync(self, source, *, allow_unclassified=False):
        if not allow_unclassified:
            raise ValueError("AV classification handoff is not integrated yet. Use --allow-unclassified only for development validation.")
        with source.connect() as connection, self._writer() as db:
            records = connection.execution_options(stream_results=True).execute(
                text("SELECT * FROM silver.cleaned_job_postings ORDER BY deduplication_key")
            ).mappings()
            return SilverSync(db).run(records)

    def validate(self, records):
        with Session(self.destination) as db:
            return validate_records(db, records)

    def import_categories(self, records):
        with self._writer() as db:
            return import_categories(db, records)
