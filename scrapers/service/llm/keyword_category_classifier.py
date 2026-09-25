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
    bounded by that vocabulary's coverage - jobs matching none of the
    categories' keywords return an empty tuple and should fall back to the
    LLM (job_enricher.py), since every AV-relevant job needs at least one
    category by the taxonomy's own rule.
    """

    def __init__(self) -> None:
        self._categories = _load_category_patterns()

    def _match_counts(self, text: str) -> dict[str, int]:
        counts = {}
        for name, patterns in self._categories:
            # Count of distinct keyword phrases that matched at least once -
            # not total occurrences, so a phrase repeated five times still
            # counts once - used to weight which main_type group wins a tie
            # instead of just how many sub_types matched.
            match_count = sum(1 for pattern in patterns if pattern.search(text))
            if match_count:
                counts[name] = match_count
        return counts

    def classify(self, text: str, title: str | None = None) -> tuple[str, ...]:
        """`title`, when given, is checked on its own first: a category
        named in the title decides the result outright, the same
        title-decides-first rule the LLM prompt follows (categories_
        definition.txt).

        When a title is given but doesn't decide it, this does NOT fall
        through to matching the rest of `text` - unlike a title, an
        arbitrary sentence in the body has no reason to be *about* the
        role's own category. A company's "about us" paragraph regularly
        lists its other departments ("...machine learning and robotics,
        cloud platforms, mapping, sensors and compute systems, systems and
        safety engineering...") - real jobs at Latitude AI whose title had
        nothing to do with mapping (a cybersecurity engineer, a fullstack
        engineer, several vehicle test/mission operators, a bench
        technician) were all silently keyword-matched to Mapping this way,
        purely because that boilerplate sentence happens to contain the
        word "mapping". A blind keyword count can't tell "this describes
        the role" from "this describes the company's other teams" - that
        distinction needs real context, which is what the LLM path (with
        its explicit boilerplate-immunity instructions) is for. Returning
        empty here defers to it, per this class's own documented contract.

        Only when no title is supplied at all (the caller has no title/body
        split to offer) does this fall back to matching the whole `text` -
        preserving the original whole-text behavior for that case.
        """
        if title:
            title_weights = self._match_counts(title)
            return constrain_to_dominant_main_type(tuple(title_weights), weights=title_weights)

        weights = self._match_counts(text)
        return constrain_to_dominant_main_type(tuple(weights), weights=weights)
