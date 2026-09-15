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
