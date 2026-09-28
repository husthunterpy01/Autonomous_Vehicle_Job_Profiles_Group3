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
#
# Same reasoning applies to generic ML/AI terms: harshil_doc_0308.md treats
# "Machine Learning" itself as ambiguous across categories ("A role
# mentioning nuScenes may relate to Perception, Prediction, or Machine
# Learning"), not a Perception signal. Perception's Keywords: line briefly
# included "machine learning"/"deep learning"/"neural network" - not part of
# the original researched taxonomy (martin_doc_0208.md's Perception row has
# neither) - and because those terms show up in nearly every AV ML job's
# description or even a company's boilerplate "about us" paragraph
# regardless of the actual role, the keyword classifier's group-weighting
# tie-break let them hijack unrelated jobs (Linux Kernel, Developer
# Relations, IC design) into Perception. Kept here as skills worth
# extracting, same as the dataset names above, without letting them decide
# a category.
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
    "machine learning",
    "deep learning",
    "neural network",
    # Specific languages, frameworks/libraries/simulators/standards named in
    # AV postings' requirements. Bare "ROS" is a plain term here; extract()
    # drops it when the more specific "ROS 1"/"ROS 2" also matched. Short
    # single-letter language names ("C", "Go", "R") stay out - they would
    # false-match ordinary text ("Go" is matched only as "Golang", and
    # "Swift" is left out because it is also a common adjective).
    "Python",
    "C++",
    "MATLAB",
    "Java",
    "Rust",
    "Golang",
    "C#",
    "Kotlin",
    "Scala",
    "Lua",
    "JavaScript",
    "TypeScript",
    "SQL",
    "Bash",
    "Verilog",
    "SystemVerilog",
    "VHDL",
    "Objective-C",
    "ROS",
    "PyTorch",
    "TensorFlow",
    "ONNX",
    "OpenCV",
    "PCL",
    "Point Cloud Library",
    "CUDA",
    "cuDNN",
    "Autoware",
    "AUTOSAR",
    "ROS 1",
    "ROS1",
    "CARLA",
    "LGSVL",
    "OpenDRIVE",
    "OpenSCENARIO",
    "Isaac Sim",
    "GTSAM",
    "g2o",
    "Ceres Solver",
    # Tooling, OS and hardware platforms.
    "Linux",
    "Git",
    "Bazel",
    "CMake",
    "Simulink",
    "QNX",
    "Jetson",
    "CANoe",
    "dSPACE",
    # AV terminology not covered by the category keyword lines.
    "ADAS",
    "V2X",
    "GNSS",
    "IMU",
    "RTK",
    "Kalman filter",
    "particle filter",
    "visual odometry",
    "visual SLAM",
    "lane detection",
    "behavior planning",
    "trajectory optimization",
    "Hybrid A*",
    "BEV",
    "bird's-eye view",
    "bird's eye view",
    "bird\u2019s-eye view",
    "bird\u2019s eye view",
    "occupancy network",
    "end-to-end driving",
    "world model",
    "operational design domain",
    "hardware-in-the-loop",
    "software-in-the-loop",
    "ASIL",
    "UL 4600",
    "ISO 21448",
)

# Spelling variants of the additional terms above that should collapse to one
# display name (the categories_definition.txt SKILL NORMALIZATION section only
# covers the terms it already lists).
_ADDITIONAL_NORMALIZATION = {
    "golang": "Go",
    "ros1": "ROS 1",
    "point cloud library": "PCL",
    "bird's eye view": "BEV",
    "bird's-eye view": "BEV",
    "bird\u2019s eye view": "BEV",
    "bird\u2019s-eye view": "BEV",
}

# Most terms are domain concepts (sensor names, algorithm names, ROS/Apollo
# node names); this only needs to flag the minority that are actually a
# specific language/framework/tool name.
_PROGRAMMING_LANGUAGES = frozenset(
    {
        "python", "c++", "matlab", "java", "rust", "golang", "c#", "kotlin", "scala", "lua",
        "javascript", "typescript", "sql", "bash", "verilog", "systemverilog", "vhdl", "objective-c",
    }
)
_FRAMEWORKS = frozenset(
    {
        "ros", "ros 2", "ros2", "ros 1", "ros1", "rclcpp", "autoware", "cyber rt", "lanelet2", "tensorrt",
        "pytorch", "tensorflow", "onnx", "opencv", "pcl", "point cloud library", "cuda", "cudnn",
        "autosar", "carla", "lgsvl", "opendrive", "openscenario", "isaac sim", "gtsam", "g2o", "ceres solver",
    }
)
_TOOLS = frozenset(
    {
        "velodyne", "yolo", "yolox", "docker", "kubernetes", "linux", "git", "bazel", "cmake", "simulink",
        "qnx", "jetson", "canoe", "dspace",
    }
)


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
    return {**_ADDITIONAL_NORMALIZATION, **mapping}


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
        # Bare "ROS" also matches inside "ROS 2"/"ROS 1"; keep only the more
        # specific version when a posting names one.
        if "ros 1" in seen or "ros 2" in seen:
            skills = [skill for skill in skills if skill.name != "ROS"]
        return tuple(skills)
