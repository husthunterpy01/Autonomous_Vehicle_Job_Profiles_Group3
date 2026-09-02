from __future__ import annotations

import json
import logging
from hashlib import sha256

import psycopg2
from psycopg2.extras import RealDictCursor, execute_values

from scrapers.config.postgres import PostgresConfig
from scrapers.service.silver_cleaning.cleaner import SilverCleaner

logger = logging.getLogger(__name__)

SILVER_TABLE_SQL = """
CREATE SCHEMA IF NOT EXISTS silver;
CREATE TABLE IF NOT EXISTS silver.cleaned_job_postings (
    deduplication_key TEXT PRIMARY KEY,
    bronze_id TEXT,
    source_job_id TEXT,
    ats_name TEXT,
    company_name TEXT NOT NULL,
    job_name TEXT NOT NULL,
    job_description TEXT,
    headquarter TEXT,
    locations TEXT[] NOT NULL DEFAULT '{}',
    department TEXT,
    team TEXT,
    job_url TEXT,
    job_uploaded_at TIMESTAMPTZ,
    employment_type TEXT,
    workplace_type TEXT,
    ingested_at TIMESTAMPTZ
)
"""


class SilverIngest:
    """Build the cleaned, flat Silver staging table from Bronze job rows."""

    def __init__(self, postgres_config: PostgresConfig | None = None) -> None:
        self.postgres_config = postgres_config or PostgresConfig()

    def run(self) -> int:
        try:
            connection = psycopg2.connect(self.postgres_config.dsn())
            try:
                with connection:
                    records = self._read_bronze(connection)
                    cleaned = SilverCleaner.clean_records(records)
                    self._replace_silver(connection, cleaned)
            finally:
                connection.close()
            logger.info(
                "Loaded %s cleaned records into silver.cleaned_job_postings.",
                len(cleaned),
            )
            return 0
        except (OSError, RuntimeError, ValueError, psycopg2.Error) as exc:
            logger.error("Silver ingestion failed: %s", exc)
            return 1

    @staticmethod
    def _read_bronze(connection) -> list[dict]:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT * FROM bronze.job_postings")
            return [dict(row) for row in cursor.fetchall()]

    @classmethod
    def _replace_silver(cls, connection, records: list[dict]) -> None:
        with connection.cursor() as cursor:
            cursor.execute(SILVER_TABLE_SQL)
            cursor.execute("TRUNCATE TABLE silver.cleaned_job_postings")
            if not records:
                return
            execute_values(
                cursor,
                """
                INSERT INTO silver.cleaned_job_postings (
                    deduplication_key, bronze_id, source_job_id, ats_name,
                    company_name, job_name, job_description, headquarter,
                    locations, department, team, job_url, job_uploaded_at,
                    employment_type, workplace_type, ingested_at
                ) VALUES %s
                """,
                [cls._database_row(record) for record in records],
            )

    @classmethod
    def _database_row(cls, record: dict) -> tuple:
        key_payload = json.dumps(
            SilverCleaner.deduplication_key(record),
            ensure_ascii=True,
            separators=(",", ":"),
        )
        deduplication_key = sha256(key_payload.encode("utf-8")).hexdigest()
        return (
            deduplication_key,
            record["id"],
            record["source_job_id"],
            record["ats_name"],
            record["company_name"],
            record["job_name"],
            record["job_description"],
            record["headquarter"],
            list(record["locations"]),
            record["department"],
            record["team"],
            record["job_url"],
            record["job_uploaded_at"],
            record["employment_type"],
            record["workplace_type"],
            record["ingested_at"],
        )


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    return SilverIngest().run()


if __name__ == "__main__":
    raise SystemExit(main())
