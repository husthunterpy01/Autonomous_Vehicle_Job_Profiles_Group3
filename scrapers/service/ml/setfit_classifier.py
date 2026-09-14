from __future__ import annotations

from pathlib import Path

from datasets import Dataset
from setfit import SetFitModel, Trainer, TrainingArguments

_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
# Where `train` publishes fine-tuned weights (see scrapers/README.md); `load`
# falls back to this when no local copy exists, so scoring works on a fresh
# checkout without training first.
_HF_REPO_ID = "husthunterpy01/av-job-relevance-setfit"


class SetFitRelevanceClassifier:
    """Few-shot AV-relevance classifier using SetFit: contrastive fine-tuning
    of the pretrained sentence transformer's own weights on the labeled seed,
    plus a classification head - not just a frozen-embedding linear probe
    (see RelevanceClassifier/EmbeddingRelevanceClassifier for that). This is
    the standard technique for improving accuracy on a small (dozens to a
    few hundred examples) labeled set, at the cost of a slower fit() since it
    actually trains the encoder rather than just running it once.
    """

    def __init__(self, model: SetFitModel | None = None) -> None:
        self.model = model

    def fit(self, texts: list[str], labels: list[bool]) -> None:
        if len(set(labels)) < 2:
            raise ValueError("Need at least one example of each class (AV and non-AV) to train.")
        self.model = SetFitModel.from_pretrained(_MODEL_NAME)
        dataset = Dataset.from_dict({"text": texts, "label": [int(label) for label in labels]})
        args = TrainingArguments(batch_size=16, num_epochs=1, show_progress_bar=False)
        trainer = Trainer(model=self.model, args=args, train_dataset=dataset)
        trainer.train()

    def predict_proba(self, texts: list[str]) -> list[float]:
        """P(is_av_relevant) for each text. Labels were encoded 0/1 with
        True->1, so column 1 is the AV-relevant probability."""
        probabilities = self.model.predict_proba(texts)
        return [float(row[1]) for row in probabilities]

    def save(self, path: Path) -> None:
        # SetFit models are a directory (encoder + head), not a single file.
        path.mkdir(parents=True, exist_ok=True)
        self.model.save_pretrained(str(path))

    @classmethod
    def load(cls, path: Path, hf_repo_id: str | None = _HF_REPO_ID) -> "SetFitRelevanceClassifier":
        """Load the fine-tuned model from `path` if it exists locally,
        otherwise fall back to the published Hugging Face Hub repo -
        `SetFitModel.from_pretrained` accepts a repo id exactly like a local
        directory, so a fresh checkout with no local weights yet can still
        score jobs without running `train` first. Pass `hf_repo_id=None` to
        require a local copy instead."""
        source = str(path) if Path(path).is_dir() else hf_repo_id
        if not source:
            raise FileNotFoundError(f"No local SetFit model at {path} and no Hugging Face repo id to fall back to.")
        return cls(model=SetFitModel.from_pretrained(source))
