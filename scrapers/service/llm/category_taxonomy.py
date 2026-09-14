from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Mapping

from scrapers.service.llm.job_enricher import ALLOWED_CATEGORIES
from scrapers.service.llm.json_response import strip_code_fence

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "category_taxonomy.txt"
CATEGORIES_PATH = Path(__file__).resolve().parents[2] / "prompts" / "categories_definition.txt"


class CategoryTaxonomyExtractor:
    """One-time (not per-job) LLM call that groups the fixed 9-category
    taxonomy into higher-level main_type buckets.

    main_type is a property of the *category*, not of any individual job -
    the backend's Category table has one row per (taxonomy_version, sub_type)
    with no per-job dimension, so there is exactly one main_type per
    sub_type no matter how it's computed. Running this per job classification
    call would be wasteful and would risk the LLM assigning the same
    sub_type a different main_type across batches; asking it once, here, and
    freezing the result into a static mapping (scrapers/config/
    category_main_types.yaml) keeps every job's category assignment
    consistent while still letting the LLM propose the grouping.
    """

    def __init__(self, complete: Callable[[str], str]) -> None:
        self.complete = complete

    def extract(self) -> dict[str, str]:
        response = self.complete(self.build_prompt())
        return self.parse_response(response)

    @staticmethod
    def build_prompt() -> str:
        template = PROMPT_PATH.read_text(encoding="utf-8")
        categories_definition = CATEGORIES_PATH.read_text(encoding="utf-8")
        return template.replace("{{categories_definition}}", categories_definition)

    @staticmethod
    def parse_response(response: str) -> dict[str, str]:
        payload = json.loads(strip_code_fence(response))
        if not isinstance(payload, dict) or not isinstance(payload.get("categories"), list):
            raise ValueError("Expected a JSON object with a 'categories' array")

        mapping: dict[str, str] = {}
        for item in payload["categories"]:
            if not isinstance(item, Mapping):
                raise ValueError("Each category entry must be an object")
            sub_type = item.get("sub_type")
            main_type = item.get("main_type")
            if not isinstance(sub_type, str) or not isinstance(main_type, str) or not main_type.strip():
                raise ValueError("Each category entry needs a string sub_type and non-empty main_type")
            if sub_type not in ALLOWED_CATEGORIES:
                raise ValueError(f"Unknown sub_type in taxonomy response: {sub_type!r}")
            mapping[sub_type] = main_type.strip()

        missing = ALLOWED_CATEGORIES - mapping.keys()
        if missing:
            raise ValueError(f"Taxonomy response is missing categories: {sorted(missing)}")
        return mapping
