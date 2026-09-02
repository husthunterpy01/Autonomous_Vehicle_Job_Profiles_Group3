from __future__ import annotations

import logging
import sys

from scrapers.config.minio import MinioConfig
from scrapers.service.bronze_storage.bronze_ingest import BronzeIngest
from scrapers.utils.company_scraper import CompanyScraper
from scrapers.utils.parser import ScraperParser

import psycopg2

logger = logging.getLogger(__name__)

class ScraperRunner:
    @classmethod
    def scrape_data_from_sources(cls, argv: list[str] | None = None) -> int:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
            stream=sys.stderr,
        )
        args = ScraperParser.parse_args(argv)
        companies = CompanyScraper.enabled_api_sources(
            CompanyScraper.load_company_list(), company_key=args.company
        )
        if args.company and not companies:
            logger.error("No enabled API company matched key %r.", args.company)
            return 1
        if not companies:
            logger.error("No enabled API companies found.")
            return 1

        failures = 0
        archived = 0
        for company in companies:
            name = company.get("name", company.get("key"))
            try:
                archived += CompanyScraper.scrape_company(company, args.timeout)
            except (RuntimeError, ValueError, KeyError, OSError) as exc:
                logger.error("%s failed: %s", name, exc)
                failures += 1

        logger.info( "Finished %s/%s companies (%s jobs).",  len(companies) - failures,  len(companies),  archived )
        ingest_status = cls.upload_to_bronze_table()
        return 1 if failures or ingest_status else 0

    @classmethod
    def upload_to_bronze_table(cls) -> int:
        try:
            ingest_status = BronzeIngest(MinioConfig().bucket).extract_raw_data_to_db()
        except (RuntimeError, OSError, ValueError, psycopg2.Error) as exc:
            logger.error("Bronze ingest failed: %s", exc)
            return 1
        return ingest_status
