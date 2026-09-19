from __future__ import annotations

import re
from pathlib import Path

from scrapers.service.llm.category_hierarchy import constrain_to_dominant_main_type

_CATEGORIES_PATH = Path(__file__).resolve().parents[2] / "prompts" / "categories_definition.txt"
_CATEGORY_BLOCK = re.compile(r"^([A-Za-z][A-Za-z ]+) — .+\.\nKeywords: (.+)$", re.MULTILINE)


def _compile_pattern(term: str) -> re.Pattern:
    return re.compile(rf"(?<!\w){re.escape(term)}(?!\w)", re.IGNORECASE)


def _load_category_patterns() -> tuple[tuple[str, tuple[re.Pattern, ...]], ...]:
    text = _CATEGORIES_PATH.read_text(encoding="utf-8")
    categories = []
    for name, keyword_line in _CATEGORY_BLOCK.findall(text):
        terms = [t.strip() for t in keyword_line.split(",") if t.strip()]
        categories.append((name.strip(), tuple(_compile_pattern(t) for t in terms)))
    return tuple(categories)


class KeywordCategoryClassifier:
    """Deterministic, zero-LLM category assignment against the same curated
    taxonomy keyword lists already used for the LLM enrichment prompt
    (categories_definition.txt).

    Zero-shot NLI was tried for this and rejected: on a real verified example
    its category *ranking* itself was wrong (the true category placed 4th of
    9), not just its threshold - no threshold fix repairs a wrong ranking.
    This regex approach, using the same hand-curated per-category vocabulary
    that already works well for skill extraction, matched the true category
    correctly (plus one defensible extra) on the same example. Recall is
    bounded by that vocabulary's coverage - jobs matching none of the 9
    categories' keywords return an empty tuple and should fall back to the
    LLM (job_enricher.py), since every AV-relevant job needs at least one
    category by the taxonomy's own rule.
    """

    def __init__(self) -> None:
        self._categories = _load_category_patterns()

    def classify(self, text: str) -> tuple[str, ...]:
        matched = []
        weights = {}
        for name, patterns in self._categories:
            # Count of distinct keyword phrases that matched at least once -
            # not total occurrences, so a phrase repeated five times still
            # counts once - used to weight which main_type group wins a tie
            # instead of just how many sub_types matched.
            match_count = sum(1 for pattern in patterns if pattern.search(text))
            if match_count:
                matched.append(name)
                weights[name] = match_count
        return constrain_to_dominant_main_type(tuple(matched), weights=weights)
