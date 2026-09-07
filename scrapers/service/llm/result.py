from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scrapers.service.llm.decision import FilterDecision
from scrapers.service.llm.io import JobPostingIO


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
        """Write LLM candidates, audit rows, metrics, and a compact CSV report."""
        output_path = Path(output_directory)
        output_path.mkdir(parents=True, exist_ok=True)

        paths = {
            "llm_candidates": output_path / "llm_candidates.jsonl",
            "excluded_audit": output_path / "excluded_jobs.jsonl",
            "metrics": output_path / "filter_metrics.json",
            "filter_decisions": output_path / "filter_decisions.csv",
        }
        JobPostingIO.write_json_lines(paths["llm_candidates"], self.included)
        JobPostingIO.write_json_lines(paths["excluded_audit"], self.excluded)
        JobPostingIO.write_json(paths["metrics"], list(self.company_metrics))

        decision_rows = [decision.as_csv_dict() for decision in self.decisions]
        fieldnames = list(FilterDecision.__dataclass_fields__)
        JobPostingIO.write_csv(paths["filter_decisions"], decision_rows, fieldnames)
        return paths
