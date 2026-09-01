from __future__ import annotations

from typing import Any

import yaml


class CompanyRegistry:
    COMPANY_LIST_PATH = "./scrapers/data/list_companies.yaml"
    API_ATS = frozenset(
        {"greenhouse", "lever", "ashby", "smartrecruiters", "workday", "personio"}
    )

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
