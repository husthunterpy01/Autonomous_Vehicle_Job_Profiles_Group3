from __future__ import annotations

from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline


def _score_bucket(prefilter_score: int) -> str:
    if prefilter_score <= 0:
        return "prefilter_score_zero"
    if prefilter_score < 5:
        return "prefilter_score_low"
    if prefilter_score < 12:
        return "prefilter_score_medium"
    return "prefilter_score_high"


def job_text(title: str, description: str, prefilter_score: int | None = None) -> str:
    """Text representation fed to the vectorizer. The title is repeated to
    upweight it relative to the (usually longer) description, matching how
    job_prefilter's field_weights treat title matches as stronger signal.

    job_prefilter's keyword score is folded in as a repeated pseudo-word
    rather than a separate numeric feature - simpler than a mixed-type
    sklearn ColumnTransformer, and TF-IDF already treats repeated tokens as
    stronger signal, which is exactly the effect wanted here: the score is
    highly predictive (empirically, score >= 10 jobs were >90% true AV in
    manual review) but a seed of a few hundred examples alone doesn't cover
    enough vocabulary for TF-IDF text features to be confident on their own.
    """
    text = f"{title} {title} {description}"
    if prefilter_score is not None:
        bucket = _score_bucket(prefilter_score)
        text = f"{bucket} {bucket} {bucket} {text}"
    return text


class RelevanceClassifier:
    """TF-IDF + logistic regression AV-relevance classifier, distilled from a
    small LLM-labeled seed set so the remaining jobs can be scored without
    further API calls.

    TF-IDF rather than neural embeddings: job postings are short, keyword-
    dense text over a fairly fixed AV/robotics vocabulary (the same
    vocabulary job_prefilter's regex rules already key off), which is exactly
    the regime where a sparse lexical model is competitive and needs no
    pretrained-weight download.
    """

    def __init__(self, pipeline: Pipeline | None = None) -> None:
        self.pipeline = pipeline or Pipeline(
            [
                ("tfidf", TfidfVectorizer(max_features=20000, ngram_range=(1, 2), min_df=2, sublinear_tf=True)),
                ("clf", LogisticRegression(max_iter=1000, class_weight="balanced")),
            ]
        )

    def fit(self, texts: list[str], labels: list[bool]) -> None:
        if len(set(labels)) < 2:
            raise ValueError("Need at least one example of each class (AV and non-AV) to train.")
        self.pipeline.fit(texts, labels)

    def predict_proba(self, texts: list[str]) -> list[float]:
        """P(is_av_relevant) for each text."""
        class_index = list(self.pipeline.classes_).index(True)
        return [row[class_index] for row in self.pipeline.predict_proba(texts)]

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.pipeline, path)

    @classmethod
    def load(cls, path: Path) -> RelevanceClassifier:
        return cls(joblib.load(path))
