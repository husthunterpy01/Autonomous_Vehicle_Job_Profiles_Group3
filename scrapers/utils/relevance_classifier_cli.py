from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    precision_recall_fscore_support,
)
from sklearn.model_selection import train_test_split

from scrapers.service.llm import JobFilterConfig, JobPostingIO
from scrapers.service.ml.relevance_classifier import RelevanceClassifier
from scrapers.service.ml.relevance_classifier import job_text as tfidf_job_text
from scrapers.utils.job_classifier import (
    _group_by_company_title,
    _job_key,
    _load_processed_ids,
    _resolve,
    _write_line,
)

logger = logging.getLogger(__name__)


def _load_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    with path.open("r", encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def _prefilter_score(record: dict) -> int | None:
    return record.get("_prefilter", {}).get("score")


def _make_classifier(backend: str):
    if backend == "tfidf":
        return RelevanceClassifier()
    if backend == "embedding":
        from scrapers.service.ml.embedding_classifier import (
            EmbeddingRelevanceClassifier,
        )

        return EmbeddingRelevanceClassifier()
    if backend == "setfit":
        from scrapers.service.ml.setfit_classifier import SetFitRelevanceClassifier

        return SetFitRelevanceClassifier()
    if backend == "zeroshot":
        from scrapers.service.ml.zeroshot_classifier import ZeroShotRelevanceClassifier

        return ZeroShotRelevanceClassifier()
    raise ValueError(f"Unknown backend: {backend}")


def _load_classifier(backend: str, model_path: Path, hf_repo_id: str | None = None):
    if backend == "tfidf":
        return RelevanceClassifier.load(model_path)
    if backend == "embedding":
        from scrapers.service.ml.embedding_classifier import (
            EmbeddingRelevanceClassifier,
        )

        kwargs = {} if hf_repo_id is None else {"hf_repo_id": hf_repo_id or None}
        return EmbeddingRelevanceClassifier.load(model_path, **kwargs)
    if backend == "setfit":
        from scrapers.service.ml.setfit_classifier import SetFitRelevanceClassifier

        kwargs = {} if hf_repo_id is None else {"hf_repo_id": hf_repo_id or None}
        return SetFitRelevanceClassifier.load(model_path, **kwargs)
    if backend == "zeroshot":
        from scrapers.service.ml.zeroshot_classifier import ZeroShotRelevanceClassifier

        return ZeroShotRelevanceClassifier.load(model_path)
    raise ValueError(f"Unknown backend: {backend}")


def _job_text(backend: str, title: str, description: str, prefilter_score: int | None) -> str:
    if backend == "tfidf":
        return tfidf_job_text(title, description, prefilter_score)
    # Embeddings (frozen or fine-tuned via SetFit) encode natural language
    # semantics, not raw token frequency - the "prefilter_score_high"-style
    # pseudo-word trick that helps TF-IDF (it's just another token to weight)
    # carries no such meaning for a transformer encoder, so plain natural
    # text is used instead.
    return f"{title}. {title}. {description}"


def _confidence_for(probability: float) -> str:
    distance = abs(probability - 0.5)
    if distance >= 0.35:
        return "High"
    if distance >= 0.15:
        return "Medium"
    return "Low"


def train(args: argparse.Namespace) -> int:
    aliases = JobFilterConfig.load().field_aliases
    av_records = _load_jsonl(args.output_dir / "av_candidates.jsonl")
    non_av_records = _load_jsonl(args.output_dir / "non_av_jobs.jsonl")
    if args.only_llm_labeled:
        # Excludes another classifier's own predictions, which may already be
        # in these files from a prior score() run - training on ground truth
        # only avoids compounding that model's errors into this one.
        before = len(av_records) + len(non_av_records)
        av_records = [r for r in av_records if r.get("_classification", {}).get("_source") != "classifier"]
        non_av_records = [r for r in non_av_records if r.get("_classification", {}).get("_source") != "classifier"]
        logger.info(
            "Filtered to LLM-only labels: %d -> %d examples.", before, len(av_records) + len(non_av_records)
        )
    if not av_records or not non_av_records:
        raise SystemExit(
            f"Need labeled examples of both classes to train: found {len(av_records)} AV and "
            f"{len(non_av_records)} non-AV in {args.output_dir}. Run job_classifier.py --sample-size "
            "first to build a seed set."
        )

    records = av_records + non_av_records
    labels = [True] * len(av_records) + [False] * len(non_av_records)
    texts = [
        _job_text(args.backend, _resolve(r, aliases, "title"), _resolve(r, aliases, "description"), _prefilter_score(r))
        for r in records
    ]

    metrics = None
    if args.test_size > 0:
        if len(records) < 10:
            logger.warning("Too few examples (%d) for a meaningful held-out split; skipping evaluation.", len(records))
        else:
            train_texts, test_texts, train_labels, test_labels = train_test_split(
                texts, labels, test_size=args.test_size, stratify=labels, random_state=args.split_seed
            )
            eval_classifier = _make_classifier(args.backend)
            eval_classifier.fit(train_texts, train_labels)

            train_predicted = [p >= 0.5 for p in eval_classifier.predict_proba(train_texts)]
            train_precision, train_recall, train_f1, _ = precision_recall_fscore_support(
                train_labels, train_predicted, average="binary", zero_division=0
            )
            train_metrics = {
                "examples": len(train_labels),
                "accuracy": round(accuracy_score(train_labels, train_predicted), 4),
                "precision": round(train_precision, 4),
                "recall": round(train_recall, 4),
                "f1": round(train_f1, 4),
            }

            test_predicted = [p >= 0.5 for p in eval_classifier.predict_proba(test_texts)]
            precision, recall, f1, _ = precision_recall_fscore_support(
                test_labels, test_predicted, average="binary", zero_division=0
            )
            tn, fp, fn, tp = confusion_matrix(test_labels, test_predicted, labels=[False, True]).ravel()
            test_metrics = {
                "examples": len(test_labels),
                "accuracy": round(accuracy_score(test_labels, test_predicted), 4),
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1": round(f1, 4),
                "confusion_matrix": {"true_negative": int(tn), "false_positive": int(fp), "false_negative": int(fn), "true_positive": int(tp)},
            }
            metrics = {
                "train": train_metrics,
                "held_out": test_metrics,
                "overfit_gap_accuracy": round(train_metrics["accuracy"] - test_metrics["accuracy"], 4),
            }
            logger.info(
                "%s backend: train accuracy=%.3f vs held-out accuracy=%.3f (gap=%.3f) | held-out precision=%.3f recall=%.3f f1=%.3f",
                args.backend, train_metrics["accuracy"], test_metrics["accuracy"], metrics["overfit_gap_accuracy"],
                precision, recall, f1,
            )

    logger.info(
        "Training final %s classifier on all %d AV and %d non-AV seed examples.",
        args.backend, len(av_records), len(non_av_records),
    )
    classifier = _make_classifier(args.backend)
    classifier.fit(texts, labels)
    classifier.save(args.model)
    result = {"av_examples": len(av_records), "non_av_examples": len(non_av_records), "model": str(args.model)}
    if metrics is not None:
        result["evaluation"] = metrics
    print(json.dumps(result, indent=2))
    return 0


def score(args: argparse.Namespace) -> int:
    aliases = JobFilterConfig.load().field_aliases
    classifier = _load_classifier(args.backend, args.model, args.hf_repo_id)

    processed_ids = (
        _load_processed_ids(args.output_dir / "av_candidates.jsonl")
        | _load_processed_ids(args.output_dir / "non_av_jobs.jsonl")
        | _load_processed_ids(args.output_dir / "failed_jobs.jsonl")
        | _load_processed_ids(args.output_dir / "relevance_failed_jobs.jsonl")
        | _load_processed_ids(args.output_dir / "low_confidence_jobs.jsonl")
    )

    postings = JobPostingIO.load(args.input)
    pending = []
    postings_by_id: dict[str, dict] = {}
    for posting in postings:
        job_id = _job_key(posting, aliases)
        if job_id in processed_ids:
            continue
        pending.append((job_id, posting))
        postings_by_id[job_id] = posting

    representatives, dedup_map = _group_by_company_title(pending, aliases)
    logger.info("Scoring %d unlabeled (company, title) groups (%d total jobs).", len(representatives), len(pending))
    if not representatives:
        print(json.dumps({"scored": 0, "confident_av": 0, "confident_non_av": 0, "low_confidence": 0}, indent=2))
        return 0

    texts = [
        _job_text(args.backend, _resolve(posting, aliases, "title"), _resolve(posting, aliases, "description"), _prefilter_score(posting))
        for _, posting in representatives
    ]
    probabilities = classifier.predict_proba(texts)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    confident_av = confident_non_av = low_confidence = 0
    with (args.output_dir / "av_candidates.jsonl").open("a", encoding="utf-8") as av_file, (
        args.output_dir / "non_av_jobs.jsonl"
    ).open("a", encoding="utf-8") as non_av_file, (args.output_dir / "low_confidence_jobs.jsonl").open(
        "a", encoding="utf-8"
    ) as low_confidence_file:

        for (rep_id, _rep_posting), probability in zip(representatives, probabilities):
            classification = {
                "is_av_relevant": probability >= 0.5,
                "confidence": _confidence_for(probability),
                "matched_keywords": [],
                "categories": [],
                "skills": [],
                "_source": "classifier",
                "_probability": round(probability, 4),
            }
            for job_id in dedup_map.get(rep_id, [rep_id]):
                posting = postings_by_id[job_id]
                record = {**posting, "_job_id": job_id, "_classification": classification}
                if args.low_confidence_low <= probability <= args.low_confidence_high:
                    _write_line(low_confidence_file, record)
                    low_confidence += 1
                elif probability >= 0.5:
                    _write_line(av_file, record)
                    confident_av += 1
                else:
                    _write_line(non_av_file, record)
                    confident_non_av += 1

    print(
        json.dumps(
            {
                "scored_groups": len(representatives),
                "confident_av": confident_av,
                "confident_non_av": confident_non_av,
                "low_confidence": low_confidence,
                "low_confidence_file": str(args.output_dir / "low_confidence_jobs.jsonl"),
            },
            indent=2,
        )
    )
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Distill a local AV-relevance classifier from LLM-labeled seed data, then score the rest for free."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    train_parser = sub.add_parser("train", help="Fit the classifier on whatever seed labels exist")
    train_parser.add_argument("--output-dir", type=Path, default=Path("data/job_classification"))
    train_parser.add_argument("--model", type=Path, default=None, help="Defaults to relevance_model_<backend>.joblib")
    train_parser.add_argument(
        "--backend",
        choices=["tfidf", "embedding", "setfit", "zeroshot"],
        default="embedding",
        help=(
            "embedding: frozen pretrained sentence embeddings + logistic regression "
            "(default; generalizes to paraphrases TF-IDF can't match). tfidf: "
            "bag-of-words, no extra dependency. setfit: fine-tunes the transformer's "
            "own weights on the seed via contrastive learning, not just a frozen-embedding "
            "linear probe - slower to fit, overfits the small seed. "
            "embedding/setfit need sentence-transformers/setfit installed."
        ),
    )
    train_parser.add_argument(
        "--only-llm-labeled",
        action="store_true",
        help="Exclude any records already labeled by a classifier's own score() run; train on real LLM ground truth only",
    )
    train_parser.add_argument(
        "--test-size",
        type=float,
        default=0.2,
        help=(
            "Fraction of seed data held out to measure real accuracy/precision/recall before "
            "refitting on all of it for the saved model (default: 0.2; 0 skips evaluation)"
        ),
    )
    train_parser.add_argument("--split-seed", type=int, default=42, help="Random seed for the train/test split (default: 42)")

    score_parser = sub.add_parser("score", help="Score unlabeled jobs; low-confidence ones go to a re-check file")
    score_parser.add_argument("--input", required=True, type=Path)
    score_parser.add_argument("--output-dir", type=Path, default=Path("data/job_classification"))
    score_parser.add_argument("--model", type=Path, default=None, help="Defaults to relevance_model_<backend>.joblib")
    score_parser.add_argument("--backend", choices=["tfidf", "embedding", "setfit", "zeroshot"], default="embedding")
    score_parser.add_argument("--low-confidence-low", type=float, default=0.35)
    score_parser.add_argument("--low-confidence-high", type=float, default=0.65)
    score_parser.add_argument(
        "--hf-repo-id",
        default=None,
        help=(
            "--backend embedding or setfit: Hugging Face repo to fall back to when --model "
            "has no local weights (defaults: husthunterpy01/av-job-relevance-embedding or "
            "...-setfit; pass '' to require a local model instead)"
        ),
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if args.model is None:
        # setfit saves a directory (encoder + head), the others a single file.
        suffix = "" if args.backend == "setfit" else ".joblib"
        args.model = args.output_dir / f"relevance_model_{args.backend}{suffix}"
    if args.command == "train":
        return train(args)
    if args.command == "score":
        return score(args)
    raise ValueError(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
