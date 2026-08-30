from __future__ import annotations

import logging
import sys

from scrapers.utils.company_registry import CompanyRegistry
from scrapers.utils.parser import ScraperParser
from scrapers.utils.run_company import run_company

logger = logging.getLogger(__name__)


def run_scrapers(argv: list[str] | None = None) -> int:
    return ScraperRunner.run(argv)


class ScraperRunner:
    @classmethod
    def run(cls, argv: list[str] | None = None) -> int:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
            stream=sys.stderr,
        )
        args = ScraperParser.parse_args(argv)
        companies = CompanyRegistry.enabled_api_sources(
            CompanyRegistry.load_company_list(), company_key=args.company
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
                archived += run_company(company, args.max_jobs, args.timeout)
            except (RuntimeError, ValueError, KeyError, OSError) as exc:
                logger.error("%s failed: %s", name, exc)
                failures += 1

        logger.info(
            "Finished %s/%s companies (%s jobs).",
            len(companies) - failures,
            len(companies),
            archived,
        )
        return 1 if failures else 0
