from __future__ import annotations

from pathlib import Path

from transformers import pipeline

_MODEL_NAME = "facebook/bart-large-mnli"
_AV_LABEL = "autonomous vehicle engineering job"
_NON_AV_LABEL = "unrelated corporate or non-technical job"
_LABELS = [_AV_LABEL, _NON_AV_LABEL]


class ZeroShotRelevanceClassifier:
    """AV-relevance classification via zero-shot natural-language-inference
    (BART-large-MNLI) - no labeled examples needed at all, since the model
    reasons about whether the job text entails "this is an AV job" versus
    "this is an unrelated job" using knowledge from its own pretraining.

    fit() is a no-op (present for interface parity with the trained
    classifiers) - this exists as a training-free baseline to compare
    against TF-IDF, the embedding linear-probe, and SetFit fine-tuning on
    the exact same held-out split.
    """

    def __init__(self, pipe=None) -> None:
        self.pipe = pipe or pipeline("zero-shot-classification", model=_MODEL_NAME)

    def fit(self, texts: list[str], labels: list[bool]) -> None:
        if len(set(labels)) < 2:
            raise ValueError("Need at least one example of each class (AV and non-AV) to train.")
        # No parameters to fit - zero-shot uses the frozen pretrained model directly.

    def predict_proba(self, texts: list[str]) -> list[float]:
        results = self.pipe(list(texts), candidate_labels=_LABELS, multi_label=False)
        if isinstance(results, dict):
            results = [results]
        probabilities = []
        for result in results:
            label_to_score = dict(zip(result["labels"], result["scores"]))
            probabilities.append(label_to_score[_AV_LABEL])
        return probabilities

    def save(self, path: Path) -> None:
        pass  # nothing to persist - the pretrained model is loaded by name each time

    @classmethod
    def load(cls, path: Path) -> ZeroShotRelevanceClassifier:
        return cls()
