import pytest

pytest.importorskip("sentence_transformers")

from scrapers.service.ml.embedding_classifier import EmbeddingRelevanceClassifier


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
    classifier = EmbeddingRelevanceClassifier()
    with pytest.raises(ValueError, match="at least one example of each class"):
        classifier.fit(["a", "b"], [True, True])


def test_semantic_generalization_to_paraphrase_without_keyword_overlap():
    """The whole point of embeddings over TF-IDF: a self-driving-car synonym
    with zero exact token overlap with the seed should still be recognized."""
    texts, labels = _training_data()
    classifier = EmbeddingRelevanceClassifier()
    classifier.fit(texts, labels)

    probs = classifier.predict_proba(
        [
            "Staff Software Engineer working on driverless vehicle perception stacks using camera and radar.",
            "Staff Accountant handling month-end close and accounts payable.",
        ]
    )
    assert probs[0] > 0.5
    assert probs[1] < 0.5


def test_save_and_load_round_trip(tmp_path):
    texts, labels = _training_data()
    classifier = EmbeddingRelevanceClassifier()
    classifier.fit(texts, labels)

    model_path = tmp_path / "model.joblib"
    classifier.save(model_path)
    assert model_path.is_file()

    loaded = EmbeddingRelevanceClassifier.load(model_path)
    sample = ["Perception Engineer working on LiDAR fusion."]
    assert classifier.predict_proba(sample) == loaded.predict_proba(sample)


def test_load_falls_back_to_hf_when_local_path_missing(tmp_path, monkeypatch):
    downloaded = tmp_path / "hub.joblib"
    downloaded.write_bytes(b"probe")
    calls = []
    monkeypatch.setattr(
        "scrapers.service.ml.embedding_classifier.SentenceTransformer",
        lambda *args, **kwargs: "encoder",
    )
    monkeypatch.setattr(
        "scrapers.service.ml.embedding_classifier.hf_hub_download",
        lambda repo_id, filename: calls.append((repo_id, filename)) or str(downloaded),
    )
    monkeypatch.setattr(
        "scrapers.service.ml.embedding_classifier.joblib.load",
        lambda path: "probe",
    )

    loaded = EmbeddingRelevanceClassifier.load(tmp_path / "does-not-exist")

    assert calls == [("husthunterpy01/av-job-relevance-embedding", "relevance_model_embedding.joblib")]
    assert loaded.classifier == "probe"


def test_load_prefers_local_joblib_when_present(tmp_path, monkeypatch):
    local = tmp_path / "relevance_model_embedding.joblib"
    local.write_bytes(b"local")
    monkeypatch.setattr(
        "scrapers.service.ml.embedding_classifier.SentenceTransformer",
        lambda *args, **kwargs: "encoder",
    )
    monkeypatch.setattr(
        "scrapers.service.ml.embedding_classifier.hf_hub_download",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("should not hit Hub")),
    )
    monkeypatch.setattr(
        "scrapers.service.ml.embedding_classifier.joblib.load",
        lambda path: "local-probe",
    )

    loaded = EmbeddingRelevanceClassifier.load(local)

    assert loaded.classifier == "local-probe"


def test_load_honors_a_custom_hf_repo_id(tmp_path, monkeypatch):
    downloaded = tmp_path / "hub.joblib"
    downloaded.write_bytes(b"probe")
    calls = []
    monkeypatch.setattr(
        "scrapers.service.ml.embedding_classifier.SentenceTransformer",
        lambda *args, **kwargs: "encoder",
    )
    monkeypatch.setattr(
        "scrapers.service.ml.embedding_classifier.hf_hub_download",
        lambda repo_id, filename: calls.append((repo_id, filename)) or str(downloaded),
    )
    monkeypatch.setattr(
        "scrapers.service.ml.embedding_classifier.joblib.load",
        lambda path: "probe",
    )

    EmbeddingRelevanceClassifier.load(tmp_path / "does-not-exist", hf_repo_id="someone/other-repo")

    assert calls == [("someone/other-repo", "relevance_model_embedding.joblib")]


def test_load_raises_when_no_local_model_and_fallback_disabled(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "scrapers.service.ml.embedding_classifier.SentenceTransformer",
        lambda *args, **kwargs: "encoder",
    )
    with pytest.raises(FileNotFoundError, match="No local embedding model"):
        EmbeddingRelevanceClassifier.load(tmp_path / "does-not-exist", hf_repo_id=None)
