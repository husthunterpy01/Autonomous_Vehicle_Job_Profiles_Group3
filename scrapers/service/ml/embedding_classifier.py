from __future__ import annotations

from pathlib import Path

import joblib
from huggingface_hub import hf_hub_download
from sentence_transformers import SentenceTransformer
from sklearn.linear_model import LogisticRegression

_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
# Where `train` publishes the logistic probe (see scrapers/README.md); `load`
# falls back to this when no local joblib exists, so scoring works on a fresh
# checkout without training first.
_HF_REPO_ID = "husthunterpy01/av-job-relevance-embedding"
_HF_WEIGHTS = "relevance_model_embedding.joblib"


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
    def load(cls, path: Path, hf_repo_id: str | None = _HF_REPO_ID) -> EmbeddingRelevanceClassifier:
        """Load the logistic probe from `path` if it exists locally,
        otherwise download `_HF_WEIGHTS` from the published Hugging Face Hub
        repo. Pass `hf_repo_id=None` to require a local copy instead."""
        if Path(path).is_file():
            return cls(classifier=joblib.load(path))
        if not hf_repo_id:
            raise FileNotFoundError(
                f"No local embedding model at {path} and no Hugging Face repo id to fall back to."
            )
        downloaded = hf_hub_download(repo_id=hf_repo_id, filename=_HF_WEIGHTS)
        return cls(classifier=joblib.load(downloaded))
