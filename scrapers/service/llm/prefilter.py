from __future__ import annotations

import html
import json
import logging
import re
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from scrapers.service.llm.config import JobFilterConfig
from scrapers.service.llm.decision import FilterDecision
from scrapers.service.llm.result import FilterResult

logger = logging.getLogger(__name__)


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
                job_title=title,
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
            job_title=title,
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
