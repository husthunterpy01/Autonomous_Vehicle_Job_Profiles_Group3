import json

import pytest
from scrapers.service.llm import ExtractedSkill, JobEnricher, JobEnrichment


def complete_with(payload: dict) -> "callable":
    def complete(prompt: str) -> str:
        complete.last_prompt = prompt
        return json.dumps(payload)

    return complete


def test_extracts_categories_and_skills_for_a_confirmed_av_job():
    complete = complete_with(
        {
            "results": [
                {
                    "id": "job",
                    "categories": ["Perception", "Perception"],
                    "skills": [
                        {"name": "ROS 2", "skill_type": "framework"},
                        {"name": "Python", "skill_type": "programming_language"},
                    ],
                }
            ]
        }
    )

    result = JobEnricher(complete).enrich(
        "Perception Engineer", "LiDAR sensor fusion using ROS 2 and Python."
    )

    assert result == JobEnrichment(
        categories=("Perception",),
        skills=(
            ExtractedSkill("ROS 2", "framework"),
            ExtractedSkill("Python", "programming_language"),
        ),
    )


def test_prompt_embeds_taxonomy_but_not_relevance_signals():
    complete = complete_with({"results": [{"id": "job", "categories": ["Planning"], "skills": []}]})
    classifier = JobEnricher(complete)
    classifier.enrich("Engineer", "Motion planning for autonomous vehicles.")

    assert "Planning" in complete.last_prompt
    assert "UNIFIED JOB-PROFILE CATEGORY TAXONOMY" in complete.last_prompt
    assert "AV RELEVANCE SIGNALS" not in complete.last_prompt


def test_enrich_batch_with_empty_list_makes_no_request():
    calls = []

    def complete(prompt: str) -> str:
        calls.append(prompt)
        return "{}"

    assert JobEnricher(complete).enrich_batch([]) == {}
    assert calls == []


def test_unknown_category_is_skipped_and_single_job_enrich_raises():
    complete = complete_with({"results": [{"id": "job", "categories": ["Not A Real Category"], "skills": []}]})

    with pytest.raises(ValueError, match="did not return a usable enrichment"):
        JobEnricher(complete).enrich("Engineer", "Autonomous vehicle work.")


def test_missing_category_is_skipped_and_single_job_enrich_raises():
    complete = complete_with({"results": [{"id": "job", "categories": [], "skills": []}]})

    with pytest.raises(ValueError, match="did not return a usable enrichment"):
        JobEnricher(complete).enrich("Engineer", "Autonomous vehicle work.")


def test_response_missing_a_job_id_returns_partial_results_instead_of_raising():
    complete = complete_with({"results": [{"id": "a", "categories": ["Planning"], "skills": []}]})

    results = JobEnricher(complete).enrich_batch(
        [
            {"id": "a", "title": "x", "description": "y"},
            {"id": "b", "title": "x", "description": "y"},
        ]
    )

    assert "a" in results
    assert "b" not in results


def test_parses_response_wrapped_in_code_fence():
    response = """```json
{"results": [{"id": "job", "categories": ["Perception"], "skills": []}]}
```"""
    result = JobEnricher.parse_response(response, ["job"])["job"]
    assert result.categories == ("Perception",)
