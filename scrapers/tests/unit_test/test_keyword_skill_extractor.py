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


def test_extracts_specific_frameworks_and_tools_with_types():
    extractor = KeywordSkillExtractor()
    skills = extractor.extract(
        "Train models in PyTorch, deploy with CUDA and TensorRT, simulate in CARLA on Linux with Docker and Git."
    )
    by_name = {s.name: s.skill_type for s in skills}
    assert by_name.get("PyTorch") == "framework"
    assert by_name.get("CUDA") == "framework"
    assert by_name.get("CARLA") == "framework"
    assert by_name.get("Linux") == "tool"
    assert by_name.get("Docker") == "tool"
    assert by_name.get("Git") == "tool"


def test_extracts_additional_av_terminology():
    extractor = KeywordSkillExtractor()
    names = {s.name for s in extractor.extract("GNSS/IMU fusion with a Kalman filter for ADAS and V2X features.")}
    assert {"GNSS", "IMU", "Kalman filter", "ADAS", "V2X"} <= names


def test_extracts_programming_languages_and_ros():
    extractor = KeywordSkillExtractor()
    by_name = {s.name: s.skill_type for s in extractor.extract("Strong Python, C++ and MATLAB; ROS experience.")}
    assert by_name == {
        "Python": "programming_language",
        "C++": "programming_language",
        "MATLAB": "programming_language",
        "ROS": "framework",
    }


def test_extracts_other_programming_languages():
    extractor = KeywordSkillExtractor()
    text = "Java, Rust, Golang, C#, Kotlin, TypeScript, JavaScript, SQL, Bash, Verilog, VHDL and Objective-C."
    by_name = {s.name: s.skill_type for s in extractor.extract(text)}
    expected = {"Java", "Rust", "Go", "C#", "Kotlin", "TypeScript", "JavaScript", "SQL", "Bash", "Verilog", "VHDL", "Objective-C"}
    assert expected <= set(by_name)
    assert all(by_name[name] == "programming_language" for name in expected)


def test_language_names_respect_word_boundaries():
    extractor = KeywordSkillExtractor()
    names = {s.name for s in extractor.extract("We use PostgreSQL and MySQL; a swift decision, then go ahead.")}
    assert names.isdisjoint({"SQL", "Go", "Swift"})
    assert {s.name for s in extractor.extract("JavaScript only")} == {"JavaScript"}


def test_bare_ros_is_dropped_when_a_specific_ros_version_matches():
    extractor = KeywordSkillExtractor()
    names = {s.name for s in extractor.extract("ROS and ROS 2 nodes in C++.")}
    assert "ROS 2" in names
    assert "ROS" not in names
    assert "C++" in names


def test_single_letter_language_names_do_not_match():
    extractor = KeywordSkillExtractor()
    assert extractor.extract("Plan A, option C, and a Go/No-Go review; use R for analysis.") == ()


def test_new_terms_respect_word_boundaries_and_normalize_variants():
    extractor = KeywordSkillExtractor()
    assert extractor.extract("Hosted on GitHub and GitLab, not plain source control.") == ()
    names = [s.name for s in extractor.extract("Bird’s-eye view perception (BEV), bird's eye view, and ROS1.")]
    assert names.count("BEV") == 1
    assert "ROS 1" in names
