from scrapers.service.llm.keyword_skill_extractor import KeywordSkillExtractor


def test_extracts_bare_sensor_terms():
    extractor = KeywordSkillExtractor()
    skills = extractor.extract("We use sensor information from Camera, LiDAR and Radar.")
    names = {s.name for s in skills}
    assert {"camera", "LiDAR", "radar"} <= names


def test_extracts_cross_cutting_framework_terms_not_in_categories_file():
    extractor = KeywordSkillExtractor()
    skills = extractor.extract("Our stack is built on ROS 2, rclcpp, and Apollo Cyber RT.")
    by_name = {s.name: s.skill_type for s in skills}
    assert by_name.get("ROS 2") == "framework"
    assert by_name.get("rclcpp") == "framework"
    assert by_name.get("Cyber RT") == "framework"


def test_extracts_dataset_names_as_domain_concept():
    extractor = KeywordSkillExtractor()
    skills = extractor.extract("Benchmarked against the Waymo Open Dataset, nuScenes, and KITTI.")
    by_name = {s.name: s.skill_type for s in skills}
    assert by_name.get("Waymo Open Dataset") == "domain_concept"
    assert by_name.get("nuScenes") == "domain_concept"
    assert by_name.get("KITTI") == "domain_concept"


def test_does_not_extract_removed_false_positive_terms():
    extractor = KeywordSkillExtractor()
    skills = extractor.extract(
        "Monitor compliance deadlines. Benefits include Kaiser Permanente, Anthem, and Guardian dental."
    )
    names = {s.name for s in skills}
    assert "Monitor" not in names
    assert "Guardian" not in names


def test_deduplicates_and_normalizes_variants():
    extractor = KeywordSkillExtractor()
    skills = extractor.extract("Experience with ROS2 and ROS 2 both required. Also lidar and LiDAR.")
    names = [s.name for s in skills]
    assert names.count("ROS 2") == 1
    assert names.count("LiDAR") == 1


def test_returns_empty_for_no_matches():
    extractor = KeywordSkillExtractor()
    assert extractor.extract("General office administration and scheduling.") == ()
