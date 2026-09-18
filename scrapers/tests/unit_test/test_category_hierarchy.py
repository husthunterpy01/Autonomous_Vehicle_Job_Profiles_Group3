from scrapers.service.llm.category_hierarchy import (
    constrain_to_dominant_main_type,
    load_main_types,
)

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


def test_load_main_types_returns_the_real_checked_in_mapping():
    mapping = load_main_types()
    assert mapping["Sensing"] == "Perception & Sensing"
    assert mapping["Control"] == "System"
    assert len(mapping) == 9
