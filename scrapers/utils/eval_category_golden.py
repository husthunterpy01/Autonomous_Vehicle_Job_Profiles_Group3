from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import Counter
from pathlib import Path

from scrapers.service.llm import JobEnricher, KeywordCategoryClassifier
from scrapers.service.llm.groq_client import GroqCompletion
from scrapers.service.llm.text import compress_job_text
from scrapers.utils.job_classifier import _batch_call_with_retry, _chunk

DEFAULT_GOLDEN = Path(__file__).resolve().parents[1] / "data" / "regression" / "category_golden.json"
NO_CATEGORY = "NONE"

logger = logging.getLogger(__name__)


def load_golden(path: Path = DEFAULT_GOLDEN) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def is_correct(expected: str, predicted: tuple[str, ...]) -> bool:
    if expected == NO_CATEGORY:
        return not predicted
    return expected in predicted


def classify_once(golden: list[dict], batch_size: int) -> list[tuple[str, ...]]:
    """One pass mirroring the real pipeline: the deterministic keyword
    classifier first, then the LLM for whatever it can't resolve."""
    keyword_classifier = KeywordCategoryClassifier()
    enricher = JobEnricher(GroqCompletion())
    predictions: dict[int, tuple[str, ...]] = {}
    pending = []
    for index, job in enumerate(golden):
        title, description = compress_job_text(job["title"], job["description"], 2200)
        keyword_categories = keyword_classifier.classify(f"{title} {description}", title=title)
        if keyword_categories:
            predictions[index] = keyword_categories
        else:
            pending.append((index, {"id": str(index), "title": title, "description": description}))

    for batch_number, batch in enumerate(_chunk(pending, batch_size), start=1):
        jobs_by_id = {job["id"]: job for _, job in batch}
        results = _batch_call_with_retry(
            enricher.enrich_batch, jobs_by_id, batch_number, -1, label="golden-eval"
        )
        for index, job in batch:
            enrichment = results.get(job["id"])
            predictions[index] = enrichment.categories if enrichment else ("<failed>",)
    return [predictions[i] for i in range(len(golden))]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Score the category classifier against the hand-verified golden set and measure "
        "run-to-run consistency. Needs Groq quota; run it after every prompt change."
    )
    parser.add_argument("--golden", type=Path, default=DEFAULT_GOLDEN)
    parser.add_argument("--repeats", type=int, default=1, help="runs per job; >1 also reports consistency")
    parser.add_argument("--batch-size", type=int, default=3)
    parser.add_argument("--min-accuracy", type=float, default=0.9)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s: %(message)s")

    golden = load_golden(args.golden)
    runs = [classify_once(golden, args.batch_size) for _ in range(args.repeats)]

    correct = 0
    stable = 0
    for index, job in enumerate(golden):
        outcomes = [tuple(sorted(run[index])) for run in runs]
        modal, modal_count = Counter(outcomes).most_common(1)[0]
        stable += modal_count == len(outcomes)
        ok = is_correct(job["expected"], modal)
        correct += ok
        if not ok or modal_count != len(outcomes):
            flag = "WRONG " if not ok else "UNSTABLE"
            print(f"{flag} {job['company']} | {job['title']}: expected {job['expected']}, got {sorted(set(outcomes))}")

    total = len(golden)
    accuracy = correct / total
    print(f"accuracy {correct}/{total} = {accuracy:.0%}; consistent across {args.repeats} run(s): {stable}/{total}")
    return 0 if accuracy >= args.min_accuracy else 1


if __name__ == "__main__":
    sys.exit(main())
