from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from scrapers.service.llm.json_response import (
    build_batch_prompt,
    parse_batch_response,
)

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "av_function_filter.txt"

ALLOWED_CONFIDENCE = frozenset({"High", "Medium", "Low"})

# Broad-recall title signals for non-engineering functions (program/product
# management, operations, policy, sales/commercial, recruiting, HR,
# executive-generalist). Deliberately over-inclusive: this only decides
# which jobs are worth an LLM call, never the exclude decision itself - see
# AVFunctionFilter, which is what actually confirms or clears a flagged job
# against its full description. A regex alone proved unreliable for this
# during the Infrastructure-category audit this list is drawn from (e.g.
# "Senior Staff Regulatory and Compliance Systems Engineer" reads like a
# policy title but is genuinely hands-on engineering work).
_NON_ENGINEERING_TITLE_PATTERN = re.compile(
    r"\b("
    r"product\s+manager|program\s+manager|project\s+manager|"
    r"technical\s+program\s+manager|technical\s+project\s+manager|"
    r"sourcer|sourcing\s+manager|"
    r"operations?\s+manager|operations?\s+coordinator|"
    r"policy\s+advisor|policy\s+manager|"
    r"commercial\s+(lead|manager)|strategic\s+partner\s+manager|"
    r"account\s+manager|partner\s+manager|"
    r"compensation\s+(and\s+benefits\s+)?analyst|"
    r"site\s+operations\s+manager|technical\s+operations\s+manager|"
    r"site\s+lead|field\s+lead|deployment\s+lead|site\s+manager|"
    r"field\s+operations|"
    r"talent\s+management|recruiter|"
    r"business\s+development|sales\s+(manager|lead|engineer)?|"
    r"marketing\s+manager|"
    r"chief\s+of\s+staff"
    r")\b",
    re.IGNORECASE,
)

# A flagged title that also names a hands-on IC/specialist discipline is
# still sent to the LLM (never auto-excluded on the regex alone) - this only
# widens which flagged jobs get a closer look in _run_function_filter_stage,
# it doesn't skip the LLM call.
_ENGINEERING_TITLE_GUARD = re.compile(
    r"\b(engineer|engineering|developer|scientist|technician|architect|researcher|programmer)\b",
    re.IGNORECASE,
)


def title_flags_review(title: str) -> bool:
    """True when `title` matches a broad-recall non-engineering-function
    signal and should be sent to the LLM for a real decision.

    This is a recall-only pre-filter, not a verdict: it exists purely to
    keep the common case (an unambiguous engineering title) from spending a
    Groq call at all, mirroring how KeywordCategoryClassifier is a free
    pass-1 in front of JobEnricher. Whether a flagged job actually gets
    excluded is always decided by AVFunctionFilter reading the full
    description, never by this function alone.
    """
    return bool(_NON_ENGINEERING_TITLE_PATTERN.search(title))


def title_has_engineering_guard(title: str) -> bool:
    """True when `title` also names a hands-on IC/specialist discipline.

    Informational only (surfaced in output for audit purposes) - it does not
    change whether a flagged job is sent to the LLM or how its result is
    applied, since a title combining both a business-function word and an
    engineering word (e.g. "Engineering Program Manager") is exactly the
    ambiguous case that most needs the LLM's judgment, not less of it.
    """
    return bool(_ENGINEERING_TITLE_GUARD.search(title))


@dataclass(frozen=True)
class FunctionDecision:
    is_engineering_role: bool
    confidence: str
    reason: str


class AVFunctionFilter:
    """Second-pass filter, after AV-relevance and before category/skill
    enrichment: is this AV-relevant job a hands-on engineering/technical
    role at all, or a business/program/product management, operations,
    policy, sales, recruiting, HR, or executive-generalist function that
    merely works on or near AV products?

    JobClassifier (job_classifier.py) already answers "is this about AV
    technology" - it has no reason to also judge job *function*, and
    folding that judgment into its prompt would make the AV-relevance
    signal itself less reliable. This is a distinct, narrower question asked
    only of jobs that already passed relevance, which is what keeps a
    catch-all category (historically Infrastructure) from silently
    absorbing every non-engineering AV-industry job that has nowhere else to
    go - see av_function_filter_cli.py's docstring for the full context.
    """

    def __init__(self, complete: Callable[[str], str]) -> None:
        self.complete = complete

    def classify(self, title: str, description: str) -> FunctionDecision:
        results = self.classify_batch([{"id": "job", "title": title, "description": description}])
        if "job" not in results:
            raise ValueError("LLM did not return a usable function decision for this job")
        return results["job"]

    def classify_batch(self, jobs: Sequence[Mapping[str, str]]) -> dict[str, FunctionDecision]:
        if not jobs:
            return {}
        expected_ids = [str(job["id"]) for job in jobs]
        response = self.complete(self.build_prompt(jobs))
        return self.parse_response(response, expected_ids)

    @staticmethod
    def build_prompt(jobs: Sequence[Mapping[str, str]]) -> str:
        # No second placeholder needed (unlike JobClassifier's relevance
        # signals or JobEnricher's taxonomy) - "{{__unused__}}" simply never
        # matches, so this substitutes only {{jobs_json}}.
        return build_batch_prompt(PROMPT_PATH, "{{__unused__}}", "", jobs)

    @staticmethod
    def parse_response(response: str, expected_ids: Sequence[str]) -> dict[str, FunctionDecision]:
        return parse_batch_response(response, expected_ids, AVFunctionFilter._parse_one, "function")

    @staticmethod
    def _parse_one(payload: Mapping[str, object]) -> FunctionDecision:
        is_engineering_role = payload.get("is_engineering_role")
        if not isinstance(is_engineering_role, bool):
            raise ValueError("'is_engineering_role' must be a boolean")  # noqa: TRY004 - malformed LLM JSON, not a Python type error

        confidence = str(payload.get("confidence") or "").strip().title()
        if confidence not in ALLOWED_CONFIDENCE:
            raise ValueError(f"'confidence' must be one of {sorted(ALLOWED_CONFIDENCE)}")

        reason = str(payload.get("reason") or "").strip()
        return FunctionDecision(is_engineering_role, confidence, reason)
