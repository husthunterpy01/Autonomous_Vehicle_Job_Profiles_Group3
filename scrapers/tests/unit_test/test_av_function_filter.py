import json

import pytest
from scrapers.service.llm import AVFunctionFilter, FunctionDecision, title_flags_review
from scrapers.service.llm.av_function_filter import title_has_engineering_guard


def complete_with(payload: dict) -> "callable":
    def complete(prompt: str) -> str:
        complete.last_prompt = prompt
        return json.dumps(payload)

    return complete


@pytest.mark.parametrize(
    "title",
    [
        "Senior Technical Program Manager, Simulation",
        "Product Manager - Platform",
        "Senior Technical Sourcer",
        "Site Operations Manager II",
        "Policy Advisor",
        "Strategic Partner Manager, Commercialization",
        "Compensation and Benefits Analyst",
    ],
)
def test_title_flags_review_matches_known_non_engineering_titles(title):
    assert title_flags_review(title) is True


@pytest.mark.parametrize(
    "title",
    [
        "Perception Engineer",
        "Senior Embedded Software Engineer - Firmware",
        "Senior Staff Regulatory and Compliance Systems Engineer",
        "Test Engineer",
        "Engineering Technician",
    ],
)
def test_title_flags_review_leaves_engineering_titles_alone(title):
    assert title_flags_review(title) is False


def test_title_has_engineering_guard_detects_combined_titles():
    assert title_has_engineering_guard("Engineering Program Manager") is True
    assert title_has_engineering_guard("Product Manager - Platform") is False


def test_classifies_engineering_role():
    complete = complete_with(
        {
            "results": [
                {
                    "id": "job",
                    "is_engineering_role": True,
                    "confidence": "High",
                    "reason": "Hands-on embedded OS development",
                }
            ]
        }
    )

    result = AVFunctionFilter(complete).classify(
        "Embedded Software Engineer - Core OS", "Develop the real-time embedded OS."
    )

    assert result == FunctionDecision(
        is_engineering_role=True, confidence="High", reason="Hands-on embedded OS development"
    )


def test_classifies_non_engineering_role():
    complete = complete_with(
        {
            "results": [
                {
                    "id": "job",
                    "is_engineering_role": False,
                    "confidence": "High",
                    "reason": "Program management, not hands-on engineering",
                }
            ]
        }
    )

    result = AVFunctionFilter(complete).classify(
        "Senior Technical Program Manager, Simulation", "Drive cross-functional roadmaps."
    )

    assert result.is_engineering_role is False


def test_prompt_embeds_jobs_json():
    complete = complete_with(
        {"results": [{"id": "job", "is_engineering_role": True, "confidence": "High", "reason": "x"}]}
    )
    function_filter = AVFunctionFilter(complete)
    function_filter.classify("Test Engineer", "Runs test rigs.")

    assert '"title": "Test Engineer"' in complete.last_prompt or '"title":"Test Engineer"' in complete.last_prompt
    assert "Runs test rigs." in complete.last_prompt


def test_classify_batch_with_empty_list_makes_no_request():
    calls = []

    def complete(prompt: str) -> str:
        calls.append(prompt)
        return "{}"

    assert AVFunctionFilter(complete).classify_batch([]) == {}
    assert calls == []


def test_invalid_confidence_is_skipped_and_single_job_classify_raises():
    complete = complete_with(
        {"results": [{"id": "job", "is_engineering_role": True, "confidence": "Certain", "reason": "x"}]}
    )

    with pytest.raises(ValueError, match="did not return a usable function decision"):
        AVFunctionFilter(complete).classify("Engineer", "Description.")


def test_response_missing_a_job_id_returns_partial_results_instead_of_raising():
    complete = complete_with(
        {"results": [{"id": "a", "is_engineering_role": True, "confidence": "High", "reason": "x"}]}
    )

    results = AVFunctionFilter(complete).classify_batch(
        [
            {"id": "a", "title": "x", "description": "y"},
            {"id": "b", "title": "x", "description": "y"},
        ]
    )

    assert "a" in results
    assert "b" not in results


def test_parses_response_wrapped_in_code_fence():
    response = """```json
{"results": [{"id": "job", "is_engineering_role": false, "confidence": "Low", "reason": "x"}]}
```"""
    result = AVFunctionFilter.parse_response(response, ["job"])["job"]
    assert result.is_engineering_role is False
