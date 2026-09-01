from __future__ import annotations

import logging
from typing import Any

from scrapers.strategy.apistrategy import APIStrategy

logger = logging.getLogger(__name__)


def run_company(company: dict[str, Any], max_jobs: int, timeout: float) -> int:
    name = company["name"]
    slug = company.get("slug")
    if not slug:
        logger.warning("Skipping %s: API company is missing a slug.", name)
        return 0

    logger.info("Fetching %s jobs from %s.", name, company["ats"])
    strategy = APIStrategy(
        ats_name=company["ats"],
        slug=slug,
        company_name=name,
    )
    jobs = strategy.fetch_postings(max_jobs=max_jobs, timeout=timeout)
    logger.info("Archived %s %s jobs from %s.", len(jobs), name, company["ats"])
    return len(jobs)
