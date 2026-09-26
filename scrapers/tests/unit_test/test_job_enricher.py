import json

import pytest
from scrapers.service.llm import ExtractedSkill, JobEnricher, JobEnrichment
from scrapers.service.llm.job_enricher import parse_categories_with_confidence


def complete_with(payload: dict) -> "callable":
    def complete(prompt: str) -> str:
        complete.last_prompt = prompt
        return json.dumps(payload)

    return complete


def _category(name: str, confidence: str = "High") -> dict:
    return {"name": name, "confidence": confidence}


def test_extracts_categories_and_skills_for_a_confirmed_av_job():
    complete = complete_with(
        {
            "results": [
                {
                    "id": "job",
                    "categories": [_category("Perception"), _category("Perception")],
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
    complete = complete_with({"results": [{"id": "job", "categories": [_category("Planning")], "skills": []}]})
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
    complete = complete_with({"results": [{"id": "job", "categories": [_category("Not A Real Category")], "skills": []}]})

    with pytest.raises(ValueError, match="did not return a usable enrichment"):
        JobEnricher(complete).enrich("Engineer", "Autonomous vehicle work.")


def test_explicit_empty_categories_means_no_fit_and_is_not_an_error():
    complete = complete_with({"results": [{"id": "job", "area": "", "evidence": "", "categories": [], "skills": []}]})

    result = JobEnricher(complete).enrich("Business Systems Engineer", "NetSuite and Workday integrations.")

    assert result.categories == ()
    assert result.has_category is False


def test_missing_categories_key_is_still_unusable_so_truncation_is_retried_not_dropped():
    complete = complete_with({"results": [{"id": "job", "skills": []}]})

    with pytest.raises(ValueError, match="did not return a usable enrichment"):
        JobEnricher(complete).enrich("Engineer", "Autonomous vehicle work.")


def test_declared_area_overrides_a_higher_weighted_category_in_another_area():
    complete = complete_with(
        {
            "results": [
                {
                    "id": "job",
                    "area": "System",
                    "evidence": "validation of controllers on HiL benches",
                    "categories": [_category("Infrastructure", "High"), _category("System and Safety", "Medium")],
                    "skills": [],
                }
            ]
        }
    )

    result = JobEnricher(complete).enrich("Systems Engineer I - Test Automation", "HiL validation.")

    assert result.categories == ("System and Safety",)
    assert result.area == "System"
    assert result.evidence == "validation of controllers on HiL benches"


def test_unknown_area_falls_back_to_the_confidence_weighted_choice():
    complete = complete_with(
        {"results": [{"id": "job", "area": "Nonsense", "categories": [_category("Planning")], "skills": []}]}
    )

    assert JobEnricher(complete).enrich("Planner", "Motion planning.").categories == ("Planning",)


def test_response_missing_a_job_id_returns_partial_results_instead_of_raising():
    complete = complete_with({"results": [{"id": "a", "categories": [_category("Planning")], "skills": []}]})

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
{"results": [{"id": "job", "categories": [{"name": "Perception", "confidence": "High"}], "skills": []}]}
```"""
    result = JobEnricher.parse_response(response, ["job"])["job"]
    assert result.categories == ("Perception",)


def test_invalid_confidence_value_is_skipped_and_single_job_enrich_raises():
    complete = complete_with(
        {"results": [{"id": "job", "categories": [{"name": "Perception", "confidence": "Extremely High"}], "skills": []}]}
    )

    with pytest.raises(ValueError, match="did not return a usable enrichment"):
        JobEnricher(complete).enrich("Engineer", "Autonomous vehicle work.")


def test_confidence_weights_break_a_tie_between_two_single_category_groups():
    # System (Control) and Decision (Planning) each have one matched
    # sub_type - without confidence weighting this would fall back to
    # response order. A High-confidence Control should beat a Low-confidence
    # Planning regardless of which the model listed first.
    complete = complete_with({
        "results": [{
            "id": "job",
            "categories": [_category("Planning", "Low"), _category("Control", "High")],
            "skills": [],
        }]
    })

    result = JobEnricher(complete).enrich("Engineer", "Autonomous vehicle work.")

    assert result.categories == ("Control",)


def test_one_high_confidence_category_beats_two_medium_confidence_ones_elsewhere():
    # The scenario that motivated ranking groups by their single strongest
    # category instead of total weight: two Medium=2 categories in Decision
    # (summing to 4) must not outrank one High=3 category in System, since
    # quantity of medium guesses shouldn't out-vote one strong signal.
    complete = complete_with({
        "results": [{
            "id": "job",
            "categories": [
                _category("Control", "High"),
                _category("Planning", "Medium"),
                _category("Prediction", "Medium"),
            ],
            "skills": [],
        }]
    })

    result = JobEnricher(complete).enrich("Engineer", "Autonomous vehicle work.")

    assert result.categories == ("Control",)


def test_parse_categories_with_confidence_returns_name_confidence_pairs_in_order():
    result = parse_categories_with_confidence([_category("Perception", "High"), _category("Sensing", "Medium")])
    assert result == (("Perception", "High"), ("Sensing", "Medium"))


def test_parse_categories_with_confidence_dedupes_by_name_keeping_first():
    result = parse_categories_with_confidence([_category("Perception", "Low"), _category("Perception", "High")])
    assert result == (("Perception", "Low"),)


def test_parse_categories_with_confidence_normalizes_confidence_case():
    result = parse_categories_with_confidence([_category("Perception", "high")])
    assert result == (("Perception", "High"),)


@pytest.mark.parametrize("bad_value", [
    "not-a-list", [{"confidence": "High"}], [{"name": "Perception"}],
    [{"name": "Perception", "confidence": "Extremely High"}], [{"name": "", "confidence": "High"}],
])
def test_parse_categories_with_confidence_rejects_malformed_input(bad_value):
    with pytest.raises(ValueError):
        parse_categories_with_confidence(bad_value)
