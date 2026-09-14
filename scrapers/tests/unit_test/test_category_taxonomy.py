import json

import pytest

from scrapers.service.llm.category_taxonomy import CategoryTaxonomyExtractor
from scrapers.service.llm.job_enricher import ALLOWED_CATEGORIES


def _complete_with(payload: dict):
    def complete(prompt: str) -> str:
        complete.last_prompt = prompt
        return json.dumps(payload)

    return complete


def _full_valid_payload(overrides: dict | None = None) -> dict:
    mapping = {name: "Group A" for name in ALLOWED_CATEGORIES}
    if overrides:
        mapping.update(overrides)
    return {"categories": [{"sub_type": name, "main_type": main} for name, main in mapping.items()]}


def test_extract_returns_full_mapping():
    complete = _complete_with(_full_valid_payload())

    mapping = CategoryTaxonomyExtractor(complete).extract()

    assert set(mapping.keys()) == ALLOWED_CATEGORIES
    assert all(value == "Group A" for value in mapping.values())


def test_prompt_embeds_the_fixed_taxonomy_and_forbids_changing_it():
    complete = _complete_with(_full_valid_payload())
    CategoryTaxonomyExtractor(complete).extract()

    assert "Perception" in complete.last_prompt
    assert "do not rename, merge, split, add, or remove" in complete.last_prompt.lower()


def test_rejects_unknown_sub_type():
    payload = _full_valid_payload()
    payload["categories"][0]["sub_type"] = "Not A Real Category"
    complete = _complete_with(payload)

    with pytest.raises(ValueError, match="Unknown sub_type"):
        CategoryTaxonomyExtractor(complete).extract()


def test_rejects_missing_categories():
    payload = {"categories": [{"sub_type": "Perception", "main_type": "Group A"}]}
    complete = _complete_with(payload)

    with pytest.raises(ValueError, match="missing categories"):
        CategoryTaxonomyExtractor(complete).extract()


def test_rejects_empty_main_type():
    payload = _full_valid_payload({"Perception": ""})
    complete = _complete_with(payload)

    with pytest.raises(ValueError, match="non-empty main_type"):
        CategoryTaxonomyExtractor(complete).extract()
