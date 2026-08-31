from __future__ import annotations

import logging
from typing import Any

import yaml

from scrapers.service.fetch.rawfetch import RawFetch

logger = logging.getLogger(__name__)


class CompanyScraper:
    COMPANY_LIST_PATH = "./scrapers/data/list_companies.yaml"
    API_ATS = frozenset({"greenhouse", "lever", "ashby", "smartrecruiters", "workday", "personio"})

    @classmethod
    def load_company_list(cls) -> list[dict[str, Any]]:
        with open(cls.COMPANY_LIST_PATH, encoding="utf-8") as file:
            payload = yaml.safe_load(file) or {}
        companies = payload.get("companies")
        if not isinstance(companies, list):
            raise ValueError(f"Expected a companies list in {cls.COMPANY_LIST_PATH}")
        return companies

    @classmethod
    def enabled_api_sources(
        cls, companies: list[dict[str, Any]], company_key: str | None = None
    ) -> list[dict[str, Any]]:
        selected: list[dict[str, Any]] = []
        for company in companies:
            if not company.get("enabled"):
                continue
            if company.get("ats") not in cls.API_ATS:
                continue
            if company_key and company.get("key") != company_key:
                continue
            selected.append(company)
        return selected

    @classmethod
    def scrape_company(cls, company: dict[str, Any], timeout: float) -> int:
        name = company["name"]
        ats = company.get("ats")
        if ats != "html" and not company.get("slug"):
            logger.warning("Skipping %s: API company is missing a slug.", name)
            return 0

        logger.info("Fetching %s from %s.", name, ats)
        fetcher, url = RawFetch.from_company(company)
        object_key = fetcher.fetch_and_archive(url, timeout=timeout)
        logger.info("Archived %s to %s.", name, object_key)
        return 1
