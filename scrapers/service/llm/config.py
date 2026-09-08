from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import yaml

from scrapers.service.llm.category import AuditCategoryRule

CONFIG_ENV_VAR = "AV_JOB_PREFILTER_CONFIG"
DEFAULT_CONFIG_PATH = (
    Path(__file__).resolve().parents[2] / "config" / "job_prefilter.yaml"
)


def _as_tuple(value: object, name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(
        isinstance(item, str) for item in value
    ):
        raise ValueError(f"{name} must be a YAML list of strings")
    return tuple(item.strip() for item in value if item.strip())


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

        field_weights = cls._load_field_weights(raw.get("field_weights"))
        field_aliases = cls._load_field_aliases(raw.get("field_aliases"))
        category_rules = cls._load_category_rules(
            raw.get("excluded_category_rules", [])
        )

        default_excluded_category = raw.get(
            "default_excluded_category", "Corporate / Support"
        )
        if not isinstance(default_excluded_category, str):
            raise ValueError("default_excluded_category must be a non-empty string")
        default_excluded_category = default_excluded_category.strip()
        if not default_excluded_category:
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
            excluded_category_rules=category_rules,
            default_excluded_category=default_excluded_category,
            field_aliases=field_aliases,
        )

    @staticmethod
    def _load_field_weights(value: object) -> dict[str, int]:
        if not isinstance(value, dict) or not value:
            raise ValueError("field_weights must be a non-empty mapping")

        field_weights: dict[str, int] = {}
        for field_name, weight in value.items():
            if (
                not isinstance(field_name, str)
                or not isinstance(weight, int)
                or weight < 0
            ):
                raise ValueError(
                    "field_weights must map field names to non-negative integers"
                )
            field_weights[field_name] = weight
        return field_weights

    @staticmethod
    def _load_field_aliases(value: object) -> dict[str, tuple[str, ...]]:
        if not isinstance(value, dict):
            raise ValueError("field_aliases must be a mapping")
        field_aliases = {
            name: _as_tuple(aliases, f"field_aliases.{name}")
            for name, aliases in value.items()
        }
        for required_field in ("id", "company", "title", "description"):
            if not field_aliases.get(required_field):
                raise ValueError(f"field_aliases.{required_field} is required")
        return field_aliases

    @staticmethod
    def _load_category_rules(value: object) -> tuple[AuditCategoryRule, ...]:
        if not isinstance(value, list):
            raise ValueError("excluded_category_rules must be a YAML list")

        category_rules: list[AuditCategoryRule] = []
        for index, rule in enumerate(value):
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
        return tuple(category_rules)
