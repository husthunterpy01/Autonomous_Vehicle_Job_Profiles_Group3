import json
import logging

import psycopg2
import yaml
from psycopg2.extras import Json, execute_values

from scrapers.config.dbt import DbtConfig
from scrapers.config.postgres import PostgresConfig
from scrapers.response_archive import ResponseArchive
from scrapers.service.bronze_storage.html_extractor import HTMLExtractor
from scrapers.service.bronze_storage.xml_extractor import XMLExtractor
from scrapers.utils.company_scraper import CompanyScraper

logger = logging.getLogger(__name__)

ATS_PATH = "./scrapers/data/ats_sources.yaml"

# Archive sources landed into bronze.raw_responses. "xml" and "html" payloads are
# parsed to a job list before storage; anything else (bare "html" fetches with no
# html_sources entry, etc.) is skipped.
LANDABLE_SOURCES = {"api", "xml", "html"}

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
        self._html_sources_cache = None

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
                    if source not in LANDABLE_SOURCES:
                        logger.info("Skipping %s: source %s is not landable.", company_slug, source)
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

    # Extract from API, XML feed or scraped HTML page
    def _row_from_archive(self, source, company_slug, plain_response):
        if plain_response is None or getattr(plain_response, "empty", True):
            logger.warning("Skipping %s: archive payload is empty.", company_slug)
            return None

        archive_row = plain_response.iloc[0]
        display_name = str(archive_row.get("company") or company_slug)

        body = archive_row.get("body")
        if isinstance(body, bytes):
            body = body.decode("utf-8")

        if source == "html":
            resolved = self._html_jobs(company_slug, display_name, body, archive_row.get("url"))
            if resolved is None:
                return None
            source_system, json_body = resolved
        else:
            source_system = archive_row.get("source_system")
            if source_system is None or str(source_system) in {"", "nan", "None", "html"}:
                logger.warning("Skipping %s: missing ATS source_system.", company_slug)
                return None
            if source == "xml":
                json_body = XMLExtractor(body, feed_url=archive_row.get("url")).extract_jobs()
                if not json_body:
                    logger.warning("Skipping %s: XML feed produced no jobs.", company_slug)
                    return None
            elif isinstance(body, (dict, list)):
                json_body = body
            else:
                json_body = json.loads(body)

        return (
            display_name,
            company_slug,
            source,
            str(source_system),
            Json(json_body),
            self._headquarter_for(company_slug, display_name),
            archive_row.get("fetched_at"),
        )

    def _html_jobs(self, company_slug, display_name, body, page_url):
        """Resolve the html_sources strategy for the company and run HTMLExtractor.

        Returns ``(source_system, jobs)`` or ``None`` to skip. ``source_system``
        is the company key, so each scraped site keeps its own ats_name
        downstream instead of a shared "html".
        """
        company = self._company_for(company_slug, display_name)
        key = company.get("key") if company else None
        config = self._html_sources().get(key) if key else None
        if not config:
            logger.warning("Skipping %s: no html_sources entry in %s.", company_slug, ATS_PATH)
            return None
        jobs = HTMLExtractor(body, config, page_url=page_url).extract_jobs()
        if not jobs:
            logger.warning("Skipping %s: HTML page produced no jobs.", company_slug)
            return None
        return key, jobs

    def _html_sources(self):
        if self._html_sources_cache is None:
            with open(ATS_PATH, encoding="utf-8") as file:
                config = yaml.safe_load(file) or {}
            self._html_sources_cache = config.get("html_sources") or {}
        return self._html_sources_cache

    def _headquarter_for(self, company_slug, display_name):
        company = self._company_for(company_slug, display_name)
        return company.get("country") if company else None

    def _company_for(self, company_slug, display_name):
        if self._companies is None:
            self._companies = CompanyScraper.load_company_list()
        slug = str(company_slug).lower()
        name = str(display_name).lower() if display_name else ""
        for company in self._companies:
            company_name = str(company.get("name") or "")
            if company.get("key") == company_slug:
                return company
            if company_name.lower().replace(" ", "_") == slug:
                return company
            if company_name.lower() == name:
                return company
        return None
