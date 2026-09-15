from __future__ import annotations

import re
from pathlib import Path

from scrapers.service.llm.skill import ExtractedSkill
from scrapers.service.llm.text import normalize_text

_CATEGORIES_PATH = Path(__file__).resolve().parents[2] / "prompts" / "categories_definition.txt"
_KEYWORDS_LINE = re.compile(r"^Keywords: (.+)$", re.MULTILINE)
_NORMALIZATION_LINE = re.compile(r"^(.+?)\s*->\s*(.+)$", re.MULTILINE)

# Cross-cutting middleware/framework names and dataset/benchmark names that
# the investigation docs call out explicitly (ROS 2 and rclcpp are central to
# Autoware per martin_doc_0208.md; Cyber RT/ApolloAuto are Apollo's ROS-2
# equivalent per nimit_doc_survey.md; the dataset names are explicitly
# recommended as stored "technologies/benchmark experience" per
# harshil_doc_0308.md's recommended data fields). These live in
# av_relevance_signals.txt for the *relevance* decision, not
# categories_definition.txt, so job_enrichment.txt's Keywords: lines never
# had them - kept here rather than added to categories_definition.txt so the
# zero-shot categorizer (which treats every entry there as a job category)
# doesn't start treating "dataset name" as a 10th category.
_ADDITIONAL_KEYWORDS = (
    "ROS 2",
    "rclcpp",
    "Cyber RT",
    "ApolloAuto",
    "Waymo Open Dataset",
    "nuScenes",
    "Argoverse",
    "Argoverse 2",
    "KITTI",
    "BDD100K",
)

# Most terms are domain concepts (sensor names, algorithm names, ROS/Apollo
# node names); this only needs to flag the minority that are actually a
# specific language/framework/tool name.
_PROGRAMMING_LANGUAGES = frozenset({"python", "c++", "matlab"})
_FRAMEWORKS = frozenset({"ros 2", "ros2", "rclcpp", "autoware", "cyber rt", "lanelet2", "tensorrt"})
_TOOLS = frozenset({"velodyne", "yolo", "yolox"})


def _load_keywords() -> tuple[str, ...]:
    text = _CATEGORIES_PATH.read_text(encoding="utf-8")
    keywords: list[str] = []
    seen: set[str] = set()
    for line in _KEYWORDS_LINE.findall(text):
        for term in line.split(", "):
            term = term.strip()
            key = term.casefold()
            if term and key not in seen:
                keywords.append(term)
                seen.add(key)
    for term in _ADDITIONAL_KEYWORDS:
        key = term.casefold()
        if key not in seen:
            keywords.append(term)
            seen.add(key)
    return tuple(keywords)


def _load_normalization_map() -> dict[str, str]:
    text = _CATEGORIES_PATH.read_text(encoding="utf-8")
    section = text.split("SKILL NORMALIZATION", 1)[-1]
    mapping: dict[str, str] = {}
    for raw_terms, canonical in _NORMALIZATION_LINE.findall(section):
        canonical = canonical.strip()
        for term in raw_terms.split(","):
            mapping[term.strip().casefold()] = canonical
    return mapping


def _skill_type_for(term: str) -> str:
    normalized = term.strip().casefold()
    if normalized in _PROGRAMMING_LANGUAGES:
        return "programming_language"
    if normalized in _FRAMEWORKS:
        return "framework"
    if normalized in _TOOLS:
        return "tool"
    return "domain_concept"


def _compile_pattern(term: str) -> re.Pattern:
    # Terms containing spaces/punctuation (e.g. "point cloud", "CAN bus")
    # still need literal, case-insensitive matching; word boundaries only
    # make sense around alphanumeric edges, which re.escape already isolates.
    return re.compile(rf"(?<!\w){re.escape(term)}(?!\w)", re.IGNORECASE)


class KeywordSkillExtractor:
    """Deterministic, zero-LLM skill extraction against the same curated
    technical vocabulary already used for categorization (categories_definition.txt).

    This is the same regex-matching technique job_prefilter.py already uses
    for AV-relevance scoring, applied here to extract skills instead - no
    model call, no pretrained NER model's generic (non-AV) training data to
    fight with. Precision should be high (every term is hand-picked for this
    exact domain); recall is bounded by the vocabulary's coverage - it will
    miss skills not already in that list, unlike an LLM reading the text.
    """

    def __init__(self) -> None:
        self._normalization_map = _load_normalization_map()
        self._patterns = tuple((term, _compile_pattern(term)) for term in _load_keywords())

    def extract(self, text: str) -> tuple[ExtractedSkill, ...]:
        normalized_text = normalize_text(text)
        seen: set[str] = set()
        skills: list[ExtractedSkill] = []
        for term, pattern in self._patterns:
            if not pattern.search(normalized_text):
                continue
            display_name = self._normalization_map.get(term.casefold(), term)
            key = display_name.casefold()
            if key in seen:
                continue
            seen.add(key)
            skills.append(ExtractedSkill(name=display_name, skill_type=_skill_type_for(term)))
        return tuple(skills)
