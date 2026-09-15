import pytest

pytest.importorskip("setfit")

from scrapers.service.ml.setfit_classifier import SetFitRelevanceClassifier


def _training_data():
    av_texts = [
        "Perception Engineer. Perception Engineer. LiDAR camera fusion object detection for autonomous driving.",
        "Planning Engineer. Planning Engineer. Motion planning and trajectory generation for self-driving cars.",
        "Robotics Software Engineer. Robotics Software Engineer. ROS 2 and sensor fusion for autonomous robots.",
        "Controls Engineer. Controls Engineer. MPC and PID control for autonomous vehicle dynamics.",
    ]
    non_av_texts = [
        "Accountant. Accountant. General ledger reconciliation and financial statements.",
        "Recruiter. Recruiter. Talent acquisition and candidate sourcing pipeline.",
        "Marketing Manager. Marketing Manager. Social media campaigns and brand advertising.",
        "Legal Counsel. Legal Counsel. Commercial contracts and corporate compliance.",
    ]
    texts = av_texts + non_av_texts
    labels = [True] * len(av_texts) + [False] * len(non_av_texts)
    return texts, labels


def test_fit_requires_both_classes():
    classifier = SetFitRelevanceClassifier()
    with pytest.raises(ValueError, match="at least one example of each class"):
        classifier.fit(["a", "b"], [True, True])


def test_fit_and_predict_proba_separates_av_from_non_av():
    texts, labels = _training_data()
    classifier = SetFitRelevanceClassifier()
    classifier.fit(texts, labels)

    probs = classifier.predict_proba(
        [
            "Senior Perception Engineer working on camera and LiDAR sensor fusion for autonomous driving.",
            "Staff Accountant handling month-end close and accounts payable.",
        ]
    )
    assert probs[0] > 0.5
    assert probs[1] < 0.5


def test_load_falls_back_to_hf_repo_when_local_path_missing(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(
        "scrapers.service.ml.setfit_classifier.SetFitModel.from_pretrained",
        lambda source: calls.append(source) or "sentinel-model",
    )

    classifier = SetFitRelevanceClassifier.load(tmp_path / "does-not-exist")

    assert calls == ["husthunterpy01/av-job-relevance-setfit"]
    assert classifier.model == "sentinel-model"


def test_load_prefers_local_path_when_present(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(
        "scrapers.service.ml.setfit_classifier.SetFitModel.from_pretrained",
        lambda source: calls.append(source) or "sentinel-model",
    )
    local_dir = tmp_path / "local_model"
    local_dir.mkdir()

    SetFitRelevanceClassifier.load(local_dir)

    assert calls == [str(local_dir)]


def test_load_honors_a_custom_hf_repo_id(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(
        "scrapers.service.ml.setfit_classifier.SetFitModel.from_pretrained",
        lambda source: calls.append(source) or "sentinel-model",
    )

    SetFitRelevanceClassifier.load(tmp_path / "does-not-exist", hf_repo_id="someone/other-repo")

    assert calls == ["someone/other-repo"]


def test_load_raises_when_no_local_model_and_fallback_disabled(tmp_path):
    with pytest.raises(FileNotFoundError, match="No local SetFit model"):
        SetFitRelevanceClassifier.load(tmp_path / "does-not-exist", hf_repo_id=None)


def test_save_and_load_round_trip(tmp_path):
    texts, labels = _training_data()
    classifier = SetFitRelevanceClassifier()
    classifier.fit(texts, labels)

    model_dir = tmp_path / "setfit_model"
    classifier.save(model_dir)
    assert model_dir.is_dir()

    loaded = SetFitRelevanceClassifier.load(model_dir)
    sample = ["Perception Engineer working on LiDAR fusion."]
    original = classifier.predict_proba(sample)
    reloaded = loaded.predict_proba(sample)
    assert original == pytest.approx(reloaded, abs=1e-4)
