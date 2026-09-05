from __future__ import annotations

import csv
import html
import json
import logging
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import yaml

logger = logging.getLogger(__name__)

CONFIG_ENV_VAR = "AV_JOB_PREFILTER_CONFIG"
DEFAULT_CONFIG_PATH = (
    Path(__file__).resolve().parents[2]
    / "notebooks"
    / "config"
    / "job_prefilter.yaml"
)


def _as_tuple(value: object, name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(
        isinstance(item, str) for item in value
    ):
        raise ValueError(f"{name} must be a YAML list of strings")
    return tuple(item.strip() for item in value if item.strip())


@dataclass(frozen=True)
class AuditCategoryRule:
    name: str
    keywords: tuple[str, ...]


@dataclass(frozen=True)
class JobFilterConfig:
    minimum_score: int
    exclude_below_threshold: bool
    field_weights: Mapping[str, int]
    positive_keywords: tuple[str, ...]
    excluded_title_keywords: tuple[str, ...]
    excluded_category_rules: tuple[AuditCategoryRule, ...]
    default_excluded_category: str
    field_aliases: Mapping[str, tuple[str, ...]]

    @classmethod
    def load(cls, path: str | Path | None = None) -> "JobFilterConfig":
        configured_path = path or os.getenv(CONFIG_ENV_VAR) or DEFAULT_CONFIG_PATH
        config_path = Path(configured_path).expanduser().resolve()
        if not config_path.is_file():
            raise FileNotFoundError(f"Job pre-filter config not found: {config_path}")

        with config_path.open("r", encoding="utf-8") as stream:
            raw = yaml.safe_load(stream)

        if not isinstance(raw, dict):
            raise ValueError("Job pre-filter config must be a YAML mapping")

        minimum_score = raw.get("minimum_score")
        if not isinstance(minimum_score, int) or minimum_score < 1:
            raise ValueError("minimum_score must be a positive integer")

        exclude_below_threshold = raw.get("exclude_below_threshold", False)
        if not isinstance(exclude_below_threshold, bool):
            raise ValueError("exclude_below_threshold must be true or false")

        raw_weights = raw.get("field_weights")
        if not isinstance(raw_weights, dict) or not raw_weights:
            raise ValueError("field_weights must be a non-empty mapping")
        field_weights: dict[str, int] = {}
        for field_name, weight in raw_weights.items():
            if (
                not isinstance(field_name, str)
                or not isinstance(weight, int)
                or weight < 0
            ):
                raise ValueError("field_weights must map field names to non-negative integers")
            field_weights[field_name] = weight

        raw_aliases = raw.get("field_aliases")
        if not isinstance(raw_aliases, dict):
            raise ValueError("field_aliases must be a mapping")
        field_aliases = {
            name: _as_tuple(aliases, f"field_aliases.{name}")
            for name, aliases in raw_aliases.items()
        }
        for required_field in ("id", "company", "title", "description"):
            if not field_aliases.get(required_field):
                raise ValueError(f"field_aliases.{required_field} is required")

        raw_category_rules = raw.get("excluded_category_rules", [])
        if not isinstance(raw_category_rules, list):
            raise ValueError("excluded_category_rules must be a YAML list")
        category_rules: list[AuditCategoryRule] = []
        for index, rule in enumerate(raw_category_rules):
            if not isinstance(rule, dict) or not isinstance(rule.get("name"), str):
                raise ValueError(
                    f"excluded_category_rules[{index}] must contain a name"
                )
            category_rules.append(
                AuditCategoryRule(
                    name=rule["name"].strip(),
                    keywords=_as_tuple(
                        rule.get("keywords"),
                        f"excluded_category_rules[{index}].keywords",
                    ),
                )
            )

        default_excluded_category = raw.get(
            "default_excluded_category", "Corporate / Support"
        )
        if not isinstance(default_excluded_category, str) or not (
            default_excluded_category := default_excluded_category.strip()
        ):
            raise ValueError("default_excluded_category must be a non-empty string")

        return cls(
            minimum_score=minimum_score,
            exclude_below_threshold=exclude_below_threshold,
            field_weights=field_weights,
            positive_keywords=_as_tuple(
                raw.get("positive_keywords"), "positive_keywords"
            ),
            excluded_title_keywords=_as_tuple(
                raw.get("excluded_title_keywords"), "excluded_title_keywords"
            ),
            excluded_category_rules=tuple(category_rules),
            default_excluded_category=default_excluded_category,
            field_aliases=field_aliases,
        )


@dataclass(frozen=True)
class FilterDecision:
    job_id: str
    company: str
    included: bool
    score: int
    reason: str
    matched_keywords: tuple[str, ...]
    excluded_title_keywords: tuple[str, ...]
    audit_category: str | None
    category_evidence: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "company": self.company,
            "included": self.included,
            "score": self.score,
            "reason": self.reason,
            "matched_keywords": list(self.matched_keywords),
            "excluded_title_keywords": list(self.excluded_title_keywords),
            "audit_category": self.audit_category,
            "category_evidence": list(self.category_evidence),
        }


@dataclass(frozen=True)
class FilterResult:
    included: tuple[dict[str, Any], ...]
    excluded: tuple[dict[str, Any], ...]
    decisions: tuple[FilterDecision, ...]
    company_metrics: tuple[dict[str, Any], ...]

    @property
    def before_count(self) -> int:
        return len(self.decisions)

    @property
    def after_count(self) -> int:
        return len(self.included)

    def write_outputs(self, output_directory: str | Path) -> dict[str, Path]:
        """Write LLM candidates, excluded audit rows, and filtering metrics."""
        output_path = Path(output_directory)
        output_path.mkdir(parents=True, exist_ok=True)

        paths = {
            "llm_candidates": output_path / "llm_candidates.jsonl",
            "excluded_audit": output_path / "excluded_jobs.jsonl",
            "metrics": output_path / "filter_metrics.json",
        }
        _write_json_lines(paths["llm_candidates"], self.included)
        _write_json_lines(paths["excluded_audit"], self.excluded)
        paths["metrics"].write_text(
            json.dumps(list(self.company_metrics), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return paths


class JobPrefilter:
    """Configurable, deterministic gate for jobs sent to an LLM."""

    def __init__(self, config: JobFilterConfig):
        self.config = config
        self._positive_patterns = self._compile_patterns(config.positive_keywords)
        self._excluded_patterns = self._compile_patterns(
            config.excluded_title_keywords
        )
        self._category_patterns = tuple(
            (rule.name, self._compile_patterns(rule.keywords))
            for rule in config.excluded_category_rules
        )

    @classmethod
    def from_config(cls, path: str | Path | None = None) -> "JobPrefilter":
        return cls(JobFilterConfig.load(path))

    @staticmethod
    def _compile_patterns(
        keywords: Sequence[str],
    ) -> tuple[tuple[str, re.Pattern], ...]:
        return tuple(
            (
                keyword,
                re.compile(rf"(?<!\w){re.escape(keyword)}(?!\w)", re.IGNORECASE),
            )
            for keyword in keywords
        )

    @staticmethod
    def _normalise_text(value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, (dict, list, tuple)):
            value = json.dumps(value, ensure_ascii=False, default=str)
        plain_text = re.sub(r"<[^>]+>", " ", html.unescape(str(value)))
        return re.sub(r"\s+", " ", plain_text).strip()

    def _resolve(self, posting: Mapping[str, Any], field_name: str) -> object:
        for alias in self.config.field_aliases.get(field_name, (field_name,)):
            value = posting.get(alias)
            if value is not None and str(value).strip():
                return value
        return ""

    @staticmethod
    def _matches(
        text: str, patterns: Sequence[tuple[str, re.Pattern]]
    ) -> tuple[str, ...]:
        return tuple(keyword for keyword, pattern in patterns if pattern.search(text))

    def _categorize_excluded(
        self, posting: Mapping[str, Any], title: str
    ) -> tuple[str, tuple[str, ...]]:
        description = self._normalise_text(self._resolve(posting, "description"))
        department = self._normalise_text(self._resolve(posting, "department"))
        team = self._normalise_text(self._resolve(posting, "team"))

        # Prefer the title because company boilerplate can mention unrelated teams.
        # Use the full description next so generic titles can still be categorized.
        for text in (title, " ".join((description, department, team))):
            for category, patterns in self._category_patterns:
                evidence = self._matches(text, patterns)
                if evidence:
                    return category, evidence
        return self.config.default_excluded_category, ()

    def evaluate(self, posting: Mapping[str, Any]) -> FilterDecision:
        title = self._normalise_text(self._resolve(posting, "title"))
        job_id = self._normalise_text(self._resolve(posting, "id")) or "unknown"
        company = self._normalise_text(self._resolve(posting, "company")) or "unknown"
        excluded_matches = self._matches(title, self._excluded_patterns)

        matches_by_field: dict[str, tuple[str, ...]] = {}
        score = 0
        for field_name, weight in self.config.field_weights.items():
            text = self._normalise_text(self._resolve(posting, field_name))
            matches = self._matches(text, self._positive_patterns)
            matches_by_field[field_name] = matches
            score += weight * len(matches)

        matched_keywords = tuple(
            sorted(
                {
                    keyword
                    for matches in matches_by_field.values()
                    for keyword in matches
                }
            )
        )

        if excluded_matches:
            audit_category, category_evidence = self._categorize_excluded(
                posting, title
            )
            return FilterDecision(
                job_id=job_id,
                company=company,
                included=False,
                score=score,
                reason="excluded_title_keyword",
                matched_keywords=matched_keywords,
                excluded_title_keywords=excluded_matches,
                audit_category=audit_category,
                category_evidence=category_evidence,
            )

        score_passed = score >= self.config.minimum_score
        included = score_passed or not self.config.exclude_below_threshold
        if score_passed:
            reason = "score_at_or_above_threshold"
        elif included:
            reason = "included_for_llm_review"
        else:
            reason = "score_below_threshold"
        return FilterDecision(
            job_id=job_id,
            company=company,
            included=included,
            score=score,
            reason=reason,
            matched_keywords=matched_keywords,
            excluded_title_keywords=(),
            audit_category=None,
            category_evidence=(),
        )

    def filter(self, postings: Iterable[Mapping[str, Any]]) -> FilterResult:
        included: list[dict[str, Any]] = []
        excluded: list[dict[str, Any]] = []
        decisions: list[FilterDecision] = []

        for posting in postings:
            source_record = dict(posting)
            decision = self.evaluate(source_record)
            decisions.append(decision)
            audited_record = {**source_record, "_prefilter": decision.as_dict()}
            if decision.included:
                included.append(audited_record)
            else:
                excluded.append(audited_record)

        metrics = self._build_metrics(decisions)
        for metric in metrics:
            logger.info(
                "AV pre-filter company=%s before=%s after=%s excluded=%s reduction=%.2f%%",
                metric["company"],
                metric["before_count"],
                metric["after_count"],
                metric["excluded_count"],
                metric["reduction_percent"],
            )

        return FilterResult(
            included=tuple(included),
            excluded=tuple(excluded),
            decisions=tuple(decisions),
            company_metrics=metrics,
        )

    @staticmethod
    def _build_metrics(
        decisions: Sequence[FilterDecision],
    ) -> tuple[dict[str, Any], ...]:
        grouped: dict[str, dict[str, int]] = {}
        for decision in decisions:
            counters = grouped.setdefault(decision.company, {"before": 0, "after": 0})
            counters["before"] += 1
            counters["after"] += int(decision.included)

        metrics = []
        for company in sorted(grouped):
            before = grouped[company]["before"]
            after = grouped[company]["after"]
            excluded = before - after
            metrics.append(
                {
                    "company": company,
                    "before_count": before,
                    "after_count": after,
                    "excluded_count": excluded,
                    "reduction_percent": round((excluded / before) * 100, 2),
                }
            )
        return tuple(metrics)


def load_postings(path: str | Path) -> list[dict[str, Any]]:
    """Load a bronze-layer CSV, JSON array, or JSON Lines export."""
    input_path = Path(path)
    suffix = input_path.suffix.lower()
    if suffix == ".csv":
        with input_path.open("r", encoding="utf-8-sig", newline="") as stream:
            return [dict(row) for row in csv.DictReader(stream)]

    with input_path.open("r", encoding="utf-8") as stream:
        if suffix == ".jsonl":
            return [json.loads(line) for line in stream if line.strip()]
        payload = json.load(stream)

    if not isinstance(payload, list) or not all(
        isinstance(row, dict) for row in payload
    ):
        raise ValueError("JSON input must contain an array of job posting objects")
    return payload


def _write_json_lines(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(
                json.dumps(
                    _json_safe(row),
                    ensure_ascii=False,
                    default=str,
                    allow_nan=False,
                )
                + "\n"
            )


def _json_safe(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, Mapping):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value
