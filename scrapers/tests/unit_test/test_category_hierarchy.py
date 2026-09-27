from scrapers.service.llm.category_hierarchy import (
    constrain_to_dominant_main_type,
    load_main_types,
)
from scrapers.service.llm.job_enricher import ALLOWED_CATEGORIES

MAIN_TYPES = {
    "Sensing": "Perception",
    "Perception": "Perception",
    "Control": "System",
    "Planning": "Decision",
    "Prediction": "Decision",
}


def test_keeps_all_sub_types_when_they_share_one_main_type():
    result = constrain_to_dominant_main_type(("Sensing", "Perception"), MAIN_TYPES)
    assert result == ("Sensing", "Perception")


def test_drops_the_minority_main_type_when_categories_span_two_groups():
    # Perception area has 2 matches (Sensing, Perception), System has 1
    # (Control) - only the larger group survives.
    result = constrain_to_dominant_main_type(("Sensing", "Control", "Perception"), MAIN_TYPES)
    assert result == ("Sensing", "Perception")


def test_tie_keeps_whichever_groups_first_category_appeared_earliest():
    # Planning (Decision) and Control (System) are both singleton groups -
    # Planning appears first in the input, so its group wins the tie.
    result = constrain_to_dominant_main_type(("Planning", "Control"), MAIN_TYPES)
    assert result == ("Planning",)

    result = constrain_to_dominant_main_type(("Control", "Planning"), MAIN_TYPES)
    assert result == ("Control",)


def test_empty_input_returns_empty_tuple():
    assert constrain_to_dominant_main_type((), MAIN_TYPES) == ()


def test_unrecognized_category_falls_back_to_its_own_singleton_group():
    # A sub_type missing from the mapping shouldn't crash or vanish - it's
    # simply outranked by any real group with >=1 match.
    result = constrain_to_dominant_main_type(("Sensing", "Perception", "Not A Real Category"), MAIN_TYPES)
    assert result == ("Sensing", "Perception")


def test_weights_let_a_heavier_group_beat_a_larger_one():
    # Without weights, Perception's 2-sub_type group would beat Control's
    # 1-sub_type group on size alone. A real per-category signal (e.g.
    # keyword-match count) should be able to override that when Control's
    # single sub_type is far more strongly evidenced.
    weights = {"Sensing": 1, "Perception": 1, "Control": 10}
    result = constrain_to_dominant_main_type(("Sensing", "Perception", "Control"), MAIN_TYPES, weights=weights)
    assert result == ("Control",)


def test_weights_default_to_one_per_category_when_omitted():
    # No weights (the LLM path, which has no per-category signal) falls
    # back to ranking purely by group size, same as before this feature.
    result = constrain_to_dominant_main_type(("Sensing", "Perception", "Control"), MAIN_TYPES)
    assert result == ("Sensing", "Perception")


def test_weights_tie_still_breaks_by_earliest_category():
    # Equal total weight across groups falls back to classifier order, same
    # tie-break as the unweighted case.
    weights = {"Control": 3, "Planning": 3}
    assert constrain_to_dominant_main_type(("Planning", "Control"), MAIN_TYPES, weights=weights) == ("Planning",)
    assert constrain_to_dominant_main_type(("Control", "Planning"), MAIN_TYPES, weights=weights) == ("Control",)


def test_one_strongly_weighted_category_beats_two_weakly_weighted_ones_in_another_group():
    # Regression test: an earlier version ranked groups by *total* weight,
    # which let several weakly-evidenced categories in one group outvote a
    # single strongly-evidenced category in another (e.g. two Medium=2
    # confidences summing to 4 beating one High=3). Ranking by each group's
    # highest weight first fixes that: Control's lone weight-3 category
    # beats Decision's two weight-2 categories (3 > 2), even though
    # Decision's total (4) is larger.
    weights = {"Control": 3, "Planning": 2, "Prediction": 2}
    result = constrain_to_dominant_main_type(("Control", "Planning", "Prediction"), MAIN_TYPES, weights=weights)
    assert result == ("Control",)


def test_equal_top_weight_still_falls_back_to_total_then_order():
    # When the single strongest category is equally weighted in both groups,
    # the tie-break isn't thrown away - it falls through to total weight
    # (rewarding more matched sub_types at the same confidence), exactly as
    # it did before this feature existed.
    weights = {"Sensing": 2, "Perception": 2, "Control": 2}
    result = constrain_to_dominant_main_type(("Sensing", "Control", "Perception"), MAIN_TYPES, weights=weights)
    assert result == ("Sensing", "Perception")


def test_load_main_types_returns_the_real_checked_in_mapping():
    mapping = load_main_types()
    assert mapping["Sensing"] == "Perception & Sensing"
    assert mapping["Control"] == "System"
    assert mapping["Infrastructure"] == "Platform"
    # the checked-in YAML and the enricher's allowed list must cover the same categories
    assert set(mapping) == ALLOWED_CATEGORIES
