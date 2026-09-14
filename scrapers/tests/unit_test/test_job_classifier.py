import json

import pytest

from scrapers.service.llm import JobClassifier, RelevanceDecision


def complete_with(payload: dict) -> "callable":
    def complete(prompt: str) -> str:
        complete.last_prompt = prompt
        return json.dumps(payload)

    return complete


def test_classifies_av_relevant_job():
    complete = complete_with(
        {
            "results": [
                {
                    "id": "job",
                    "is_av_relevant": True,
                    "confidence": "High",
                    "matched_keywords": ["LiDAR", "sensor fusion", "LiDAR"],
                }
            ]
        }
    )

    result = JobClassifier(complete).classify(
        "Perception Engineer", "LiDAR sensor fusion using ROS 2 and Python."
    )

    assert result == RelevanceDecision(
        is_av_relevant=True,
        confidence="High",
        matched_keywords=("LiDAR", "sensor fusion"),
    )


def test_classifies_non_av_job():
    complete = complete_with(
        {"results": [{"id": "job", "is_av_relevant": False, "confidence": "Low", "matched_keywords": []}]}
    )

    result = JobClassifier(complete).classify("Accountant", "General ledger reconciliation.")

    assert result.is_av_relevant is False


def test_prompt_embeds_relevance_signals_and_jobs_json_but_not_categories():
    complete = complete_with(
        {"results": [{"id": "job", "is_av_relevant": False, "confidence": "Low", "matched_keywords": []}]}
    )
    classifier = JobClassifier(complete)
    classifier.classify("Engineer", "Uses Python.")

    assert '"title": "Engineer"' in complete.last_prompt or '"title":"Engineer"' in complete.last_prompt
    assert "Uses Python." in complete.last_prompt
    assert "AV RELEVANCE SIGNALS" in complete.last_prompt
    assert "UNIFIED JOB-PROFILE CATEGORY TAXONOMY" not in complete.last_prompt
    assert "SKILL NORMALIZATION" not in complete.last_prompt


def test_classify_batch_matches_results_back_to_each_job_by_id():
    complete = complete_with(
        {
            "results": [
                {"id": "b", "is_av_relevant": False, "confidence": "Low", "matched_keywords": []},
                {"id": "a", "is_av_relevant": True, "confidence": "High", "matched_keywords": ["autonomous"]},
            ]
        }
    )

    results = JobClassifier(complete).classify_batch(
        [
            {"id": "a", "title": "Planning Engineer", "description": "Autonomous vehicle motion planning."},
            {"id": "b", "title": "Accountant", "description": "General ledger."},
        ]
    )

    assert results["a"].is_av_relevant is True
    assert results["b"].is_av_relevant is False


def test_classify_batch_with_empty_list_makes_no_request():
    calls = []

    def complete(prompt: str) -> str:
        calls.append(prompt)
        return "{}"

    assert JobClassifier(complete).classify_batch([]) == {}
    assert calls == []


def test_response_missing_a_job_id_returns_partial_results_instead_of_raising():
    complete = complete_with(
        {"results": [{"id": "a", "is_av_relevant": False, "confidence": "Low", "matched_keywords": []}]}
    )

    results = JobClassifier(complete).classify_batch(
        [
            {"id": "a", "title": "x", "description": "y"},
            {"id": "b", "title": "x", "description": "y"},
        ]
    )

    assert "a" in results
    assert "b" not in results


def test_invalid_confidence_is_skipped_and_single_job_classify_raises():
    complete = complete_with(
        {"results": [{"id": "job", "is_av_relevant": False, "confidence": "Certain", "matched_keywords": []}]}
    )

    with pytest.raises(ValueError, match="did not return a usable relevance decision"):
        JobClassifier(complete).classify("Engineer", "Description.")


def test_invalid_confidence_in_one_batch_item_does_not_drop_the_rest_of_the_batch():
    complete = complete_with(
        {
            "results": [
                {"id": "a", "is_av_relevant": False, "confidence": "Certain", "matched_keywords": []},
                {"id": "b", "is_av_relevant": True, "confidence": "High", "matched_keywords": ["autonomous"]},
            ]
        }
    )

    results = JobClassifier(complete).classify_batch(
        [
            {"id": "a", "title": "x", "description": "y"},
            {"id": "b", "title": "x", "description": "y"},
        ]
    )

    assert "a" not in results
    assert results["b"].is_av_relevant is True


def test_parses_response_wrapped_in_code_fence():
    response = """```json
{"results": [{"id": "job", "is_av_relevant": false, "confidence": "Low", "matched_keywords": []}]}
```"""
    result = JobClassifier.parse_response(response, ["job"])["job"]
    assert result.is_av_relevant is False
