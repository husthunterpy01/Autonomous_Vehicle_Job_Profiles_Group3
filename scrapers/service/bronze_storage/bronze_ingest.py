import json
import logging

import psycopg2
from psycopg2.extras import Json, execute_values

from scrapers.config.dbt import DbtConfig
from scrapers.config.postgres import PostgresConfig
from scrapers.response_archive import ResponseArchive
from scrapers.utils.company_scraper import CompanyScraper

logger = logging.getLogger(__name__)

RAW_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS bronze.raw_responses (
    company_name TEXT PRIMARY KEY,
    company_slug TEXT,
    source TEXT NOT NULL,
    source_system TEXT,
    body JSONB NOT NULL,
    headquarter TEXT,
    fetched_at TIMESTAMPTZ,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
"""


class BronzeIngest():

    def __init__(self, bucket_name, postgres_config=None, dbt_config=None):
        self.bucket_name = bucket_name
        self.postgres_config = postgres_config or PostgresConfig()
        self.dbt_config = dbt_config or DbtConfig()
        self._companies = None

    def extract_raw_data_to_db(self) -> int:
        try:
            self.land_raw_responses()
        except (RuntimeError, OSError, ValueError, psycopg2.Error) as exc:
            logger.error("Failed to land MinIO payloads into bronze.raw_responses: %s", exc)
            return 1
        return self.run_dbt_bronze()

    def land_raw_responses(self):
        response_archive_inst = ResponseArchive()
        connection = psycopg2.connect(self.postgres_config.dsn())
        try:
            self._ensure_raw_table(connection)
            for source, company_slug, plain_response in response_archive_inst._extract_data_from_storage(
                bucket_name=self.bucket_name
            ):
                try:
                    if source != "api":
                        logger.info("Skipping %s: source %s is not an API payload.", company_slug, source)
                        continue
                    row = self._row_from_archive(source, company_slug, plain_response)
                    if row is None:
                        continue
                    self._upsert_raw_response(connection, row)
                    connection.commit()
                    logger.info("Landed raw payload for %s.", row[0])
                except (ValueError, KeyError, TypeError, json.JSONDecodeError, psycopg2.Error) as exc:
                    connection.rollback()
                    logger.error("%s failed: %s", company_slug, exc)
        finally:
            connection.close()

    def run_dbt_bronze(self) -> int:
        return self.dbt_config.run("+job_postings", self.postgres_config)

    def _ensure_raw_table(self, connection):
        with connection.cursor() as cursor:
            cursor.execute("CREATE SCHEMA IF NOT EXISTS bronze")
            cursor.execute(RAW_TABLE_SQL)
        connection.commit()

    def _upsert_raw_response(self, connection, row):
        with connection.cursor() as cursor:
            execute_values(
                cursor,
                """
                INSERT INTO bronze.raw_responses (
                    company_name, company_slug, source, source_system,
                    body, headquarter, fetched_at
                ) VALUES %s
                ON CONFLICT (company_name) DO UPDATE SET
                    company_slug = EXCLUDED.company_slug,
                    source = EXCLUDED.source,
                    source_system = EXCLUDED.source_system,
                    body = EXCLUDED.body,
                    headquarter = EXCLUDED.headquarter,
                    fetched_at = EXCLUDED.fetched_at,
                    ingested_at = NOW()
                """,
                [row],
            )

    def _row_from_archive(self, source, company_slug, plain_response):
        if plain_response is None or getattr(plain_response, "empty", True):
            logger.warning("Skipping %s: archive payload is empty.", company_slug)
            return None

        archive_row = plain_response.iloc[0]
        source_system = archive_row.get("source_system")
        if source_system is None or str(source_system) in {"", "nan", "None", "html"}:
            logger.warning("Skipping %s: missing ATS source_system.", company_slug)
            return None

        body = archive_row.get("body")
        if isinstance(body, bytes):
            body = body.decode("utf-8")
        if isinstance(body, (dict, list)):
            json_body = body
        else:
            json_body = json.loads(body)

        display_name = str(archive_row.get("company") or company_slug)
        return (
            display_name,
            company_slug,
            source,
            str(source_system),
            Json(json_body),
            self._headquarter_for(company_slug, display_name),
            archive_row.get("fetched_at"),
        )

    def _headquarter_for(self, company_slug, display_name):
        if self._companies is None:
            self._companies = CompanyScraper.load_company_list()
        slug = str(company_slug).lower()
        name = str(display_name).lower() if display_name else ""
        for company in self._companies:
            company_name = str(company.get("name") or "")
            if company.get("key") == company_slug:
                return company.get("country")
            if company_name.lower().replace(" ", "_") == slug:
                return company.get("country")
            if company_name.lower() == name:
                return company.get("country")
        return None
