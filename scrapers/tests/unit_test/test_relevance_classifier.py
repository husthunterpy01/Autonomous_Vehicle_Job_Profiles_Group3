import pytest

from scrapers.service.ml.relevance_classifier import RelevanceClassifier, job_text


def test_job_text_upweights_title():
    text = job_text("Perception Engineer", "Some description.")
    assert text.count("Perception Engineer") == 2


def test_job_text_folds_in_prefilter_score_bucket():
    high = job_text("Engineer", "desc", prefilter_score=15)
    zero = job_text("Engineer", "desc", prefilter_score=0)
    none = job_text("Engineer", "desc", prefilter_score=None)

    assert "prefilter_score_high" in high
    assert "prefilter_score_zero" in zero
    assert "prefilter_score" not in none


def _training_data():
    av_texts = [
        "Perception Engineer Perception Engineer LiDAR camera fusion object detection autonomous driving",
        "Planning Engineer Planning Engineer motion planning trajectory autonomous vehicle path planning",
        "Robotics Software Engineer Robotics Software Engineer ROS 2 sensor fusion autonomy robotics",
        "Controls Engineer Controls Engineer MPC PID vehicle dynamics autonomous driving controls",
    ]
    non_av_texts = [
        "Accountant Accountant general ledger reconciliation financial statements accounting",
        "Recruiter Recruiter talent acquisition sourcing candidates hiring pipeline",
        "Marketing Manager Marketing Manager social media brand campaigns advertising",
        "Legal Counsel Legal Counsel contracts compliance corporate law",
    ]
    texts = av_texts + non_av_texts
    labels = [True] * len(av_texts) + [False] * len(non_av_texts)
    return texts, labels


def test_fit_and_predict_proba_separates_av_from_non_av():
    texts, labels = _training_data()
    classifier = RelevanceClassifier()
    classifier.fit(texts, labels)

    probs = classifier.predict_proba(
        [
            "Senior Perception Engineer Senior Perception Engineer camera LiDAR sensor fusion for autonomous driving",
            "Staff Accountant Staff Accountant month end close reconciliation",
        ]
    )
    assert probs[0] > 0.5
    assert probs[1] < 0.5


def test_fit_requires_both_classes():
    classifier = RelevanceClassifier()
    with pytest.raises(ValueError, match="at least one example of each class"):
        classifier.fit(["a", "b"], [True, True])


def test_save_and_load_round_trip(tmp_path):
    texts, labels = _training_data()
    classifier = RelevanceClassifier()
    classifier.fit(texts, labels)

    model_path = tmp_path / "model.joblib"
    classifier.save(model_path)
    assert model_path.is_file()

    loaded = RelevanceClassifier.load(model_path)
    original_probs = classifier.predict_proba(["Perception Engineer LiDAR sensor fusion"])
    loaded_probs = loaded.predict_proba(["Perception Engineer LiDAR sensor fusion"])
    assert original_probs == loaded_probs
