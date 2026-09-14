from __future__ import annotations

from pathlib import Path

import joblib
from sentence_transformers import SentenceTransformer
from sklearn.linear_model import LogisticRegression

_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


class EmbeddingRelevanceClassifier:
    """Few-shot AV-relevance classifier: pretrained sentence embeddings +
    a linear probe (logistic regression), instead of an LLM call or a
    bag-of-words model.

    A frozen pretrained encoder already places semantically similar text
    close together (e.g. "self-driving" and "autonomous vehicle" land near
    each other even with zero token overlap), which is exactly what a sparse
    TF-IDF model cannot do and why it needed hundreds of examples per term to
    become confident. This lets a small labeled seed generalize much further
    - the standard "few-shot via embedding + linear probe" pattern.
    """

    def __init__(self, classifier: LogisticRegression | None = None, encoder: SentenceTransformer | None = None) -> None:
        self.encoder = encoder or SentenceTransformer(_MODEL_NAME)
        self.classifier = classifier or LogisticRegression(max_iter=1000, class_weight="balanced")

    def fit(self, texts: list[str], labels: list[bool]) -> None:
        if len(set(labels)) < 2:
            raise ValueError("Need at least one example of each class (AV and non-AV) to train.")
        embeddings = self.encoder.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        self.classifier.fit(embeddings, labels)

    def predict_proba(self, texts: list[str]) -> list[float]:
        """P(is_av_relevant) for each text."""
        embeddings = self.encoder.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        class_index = list(self.classifier.classes_).index(True)
        return [row[class_index] for row in self.classifier.predict_proba(embeddings)]

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.classifier, path)

    @classmethod
    def load(cls, path: Path) -> "EmbeddingRelevanceClassifier":
        return cls(classifier=joblib.load(path))
