import pytest

pytest.importorskip("transformers")

from scrapers.service.ml.zeroshot_classifier import ZeroShotRelevanceClassifier


def test_fit_requires_both_classes():
    classifier = ZeroShotRelevanceClassifier(pipe=lambda *a, **k: {})
    with pytest.raises(ValueError, match="at least one example of each class"):
        classifier.fit(["a", "b"], [True, True])


def test_fit_is_a_noop_given_both_classes():
    classifier = ZeroShotRelevanceClassifier(pipe=lambda *a, **k: {})
    classifier.fit(["a", "b"], [True, False])  # must not raise


def test_predict_proba_reads_av_label_score_from_pipeline_output():
    def fake_pipe(texts, candidate_labels, multi_label):
        return [
            {"labels": [candidate_labels[1], candidate_labels[0]], "scores": [0.7, 0.3]},
            {"labels": [candidate_labels[0], candidate_labels[1]], "scores": [0.9, 0.1]},
        ]

    classifier = ZeroShotRelevanceClassifier(pipe=fake_pipe)
    probs = classifier.predict_proba(["job a", "job b"])
    assert probs == [0.3, 0.9]


def test_predict_proba_handles_single_text_dict_result():
    def fake_pipe(texts, candidate_labels, multi_label):
        return {"labels": [candidate_labels[0], candidate_labels[1]], "scores": [0.6, 0.4]}

    classifier = ZeroShotRelevanceClassifier(pipe=fake_pipe)
    probs = classifier.predict_proba(["job a"])
    assert probs == [0.6]
