from scrapers.service.llm.keyword_category_classifier import KeywordCategoryClassifier


def test_matches_category_from_its_keywords():
    classifier = KeywordCategoryClassifier()
    categories = classifier.classify("We build object detection and object tracking pipelines.")
    assert categories == ("Perception",)


def test_matching_a_compound_term_can_legitimately_span_categories_in_the_same_area():
    # "camera-lidar fusion" touches both Sensing (camera hardware) and
    # Perception (fusion for scene understanding) - both belong to the same
    # Perception technical area, so keeping both is correct, not a bug.
    classifier = KeywordCategoryClassifier()
    categories = classifier.classify("We build camera-lidar fusion pipelines.")
    assert "Sensing" in categories
    assert "Perception" in categories


def test_collapses_to_one_dominant_area_when_matches_span_multiple_areas():
    # "Control" (System area) and "Planning" (Decision area) are different
    # technical areas - a job gets exactly one area, not both (see
    # category_hierarchy.constrain_to_dominant_main_type). Each area has one
    # match here, so the tie breaks to whichever area's first sub_type
    # appears earliest in categories_definition.txt (Planning, before
    # Control) - matching that file's own category ordering.
    classifier = KeywordCategoryClassifier()
    categories = classifier.classify("Own the MPC controller and PID control loop, plus motion planning for lane change.")
    assert categories == ("Planning",)


def test_returns_empty_tuple_when_nothing_matches():
    classifier = KeywordCategoryClassifier()
    assert classifier.classify("General office administration and scheduling.") == ()


def test_is_case_insensitive_and_word_bounded():
    classifier = KeywordCategoryClassifier()
    categories = classifier.classify("Experience with SLAM and pose estimation required.")
    assert "Localization" in categories
    # "SLAM" as a substring of an unrelated word must not false-match.
    no_match = classifier.classify("The islamabad office is expanding.")
    assert "Localization" not in no_match
