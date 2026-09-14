from __future__ import annotations

import json
import logging
import random
from pathlib import Path
from typing import Any, Mapping

from scrapers.service.llm import (
    JobClassifier,
    JobFilterConfig,
    JobPostingIO,
    classification_as_dict,
)
from scrapers.service.llm.groq_client import GroqCompletion
from scrapers.service.llm.text import compress_job_text, normalize_text
from scrapers.utils.parser import ScraperParser

logger = logging.getLogger(__name__)


def _resolve(posting: Mapping[str, Any], aliases: Mapping[str, tuple[str, ...]], field_name: str) -> str:
    for alias in aliases.get(field_name, (field_name,)):
        value = posting.get(alias)
        if value is not None and str(value).strip():
            return str(value)
    return ""


def _relevance_input(posting: Mapping[str, Any], aliases: Mapping[str, tuple[str, ...]], snippet_chars: int) -> str:
    """Compact stand-in for the full description in the relevance pass.

    job_prefilter already scored every job against the same positive-keyword
    list this pass would otherwise be reading raw text to rediscover -
    reusing that (free, already-computed) evidence instead of re-sending the
    full description cuts the dominant per-job cost in stage 1. A short
    excerpt is kept as a fallback for jobs prefilter matched on description
    weight alone, or none at all (score-0 jobs let through for LLM review).
    """
    keywords = posting.get("_prefilter", {}).get("matched_keywords") or []
    _, snippet = compress_job_text("", _resolve(posting, aliases, "description"), snippet_chars)
    parts = []
    if keywords:
        parts.append("Keyword matches: " + ", ".join(keywords))
    if snippet:
        parts.append("Excerpt: " + snippet)
    return " ".join(parts)


def _group_by_company_title(
    pairs: list[tuple[str, dict]], aliases: Mapping[str, tuple[str, ...]]
) -> tuple[list[tuple[str, dict]], dict[str, list[str]]]:
    """Collapse exact (company, title) duplicates to one representative job.

    Classifying the representative and propagating its result to every member
    is safe here: these are the literal same role reposted across locations
    (e.g. "Senior Software Engineer" at GM appearing 10 times), not merely
    similar text where propagation could paper over a real difference.
    """
    groups: dict[tuple[str, str], list[tuple[str, dict]]] = {}
    for job_id, posting in pairs:
        key = (_resolve(posting, aliases, "company"), _resolve(posting, aliases, "title"))
        groups.setdefault(key, []).append((job_id, posting))

    representatives = []
    dedup_map: dict[str, list[str]] = {}
    for members in groups.values():
        rep_job_id, rep_posting = max(members, key=lambda m: len(_resolve(m[1], aliases, "description")))
        representatives.append((rep_job_id, rep_posting))
        dedup_map[rep_job_id] = [job_id for job_id, _ in members]
    return representatives, dedup_map


def _load_processed_ids(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    processed: set[str] = set()
    with path.open("r", encoding="utf-8") as stream:
        for line in stream:
            line = line.strip()
            if not line:
                continue
            job_id = json.loads(line).get("_job_id")
            if job_id:
                processed.add(job_id)
    return processed


def _chunk(items: list, size: int) -> list[list]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def _count_lines(path: Path) -> int:
    if not path.is_file():
        return 0
    with path.open("r", encoding="utf-8") as stream:
        return sum(1 for line in stream if line.strip())


def _write_line(stream, record: dict[str, Any]) -> None:
    stream.write(json.dumps(JobPostingIO.json_safe(record), ensure_ascii=False, default=str) + "\n")
    stream.flush()


class JobClassifierMain:
    """AV-relevance screening (stage 1 only), resumable across interrupted runs.

    Exact (company, title) duplicates are classified once and the result
    fanned out to every repost, since Groq's free tier has a hard daily
    token budget that makes every avoidable call worth skipping. A batch
    response can come back truncated (the model runs out of completion
    budget partway through the array); missing job ids are retried once as
    their own small batch rather than discarding the whole original batch.
    Both outcomes (AV and non-AV) are persisted immediately per representative
    group - av_candidates.jsonl is a durable handoff to the enrichment stage
    (job_enricher.py) and doubles as training data for a distilled local
    classifier (see relevance_classifier.py), not just an in-memory list.

    --sample-size runs this against a random subset instead of every pending
    job - the "label a seed with the LLM" step of that distillation workflow.
    """

    @classmethod
    def main(cls, argv: list[str] | None = None) -> int:
        args = ScraperParser.parse_job_classifier_args(argv)
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )

        aliases = JobFilterConfig.load().field_aliases
        classifier = JobClassifier(GroqCompletion())

        output_dir = args.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        paths = {
            "av_candidates": output_dir / "av_candidates.jsonl",
            "non_av": output_dir / "non_av_jobs.jsonl",
            "failed": output_dir / "failed_jobs.jsonl",
            "metrics": output_dir / "relevance_metrics.json",
        }

        processed_ids = (
            _load_processed_ids(paths["av_candidates"])
            | _load_processed_ids(paths["non_av"])
            | _load_processed_ids(paths["failed"])
        )
        if processed_ids:
            logger.info("Resuming: %d jobs already classified, skipping them.", len(processed_ids))

        postings = JobPostingIO.load(args.input)
        total = len(postings)

        pending = []
        postings_by_id: dict[str, dict] = {}
        for posting in postings:
            job_id = _resolve(posting, aliases, "id") or "unknown"
            postings_by_id[job_id] = posting
            if job_id in processed_ids:
                continue
            pending.append((job_id, posting))

        skipped_count = total - len(pending)
        representatives, dedup_map = _group_by_company_title(pending, aliases)
        if len(representatives) < len(pending):
            logger.info(
                "Deduped %d pending jobs to %d unique (company, title) groups.", len(pending), len(representatives)
            )

        if args.sample_size is not None and args.sample_size < len(representatives):
            random.Random(args.sample_seed).shuffle(representatives)
            representatives = representatives[: args.sample_size]
            logger.info("Sampled %d of the pending groups for seed labeling.", len(representatives))

        with paths["non_av"].open("a", encoding="utf-8") as non_av_file, paths["av_candidates"].open(
            "a", encoding="utf-8"
        ) as av_candidates_file, paths["failed"].open("a", encoding="utf-8") as failed_file:
            av_count = cls._run_relevance_stage(
                classifier,
                aliases,
                representatives,
                dedup_map,
                postings_by_id,
                args,
                non_av_file,
                av_candidates_file,
                failed_file,
                paths,
                total,
                skipped_count,
            )

        summary = cls._write_metrics(paths, total, skipped_count)
        print(json.dumps({**summary, "outputs": {name: str(path) for name, path in paths.items()}}, indent=2))
        return 0

    @classmethod
    def _run_relevance_stage(
        cls,
        classifier,
        aliases,
        representatives,
        dedup_map,
        postings_by_id,
        args,
        non_av_file,
        av_candidates_file,
        failed_file,
        paths,
        total,
        skipped_count,
    ) -> int:
        batches = _chunk(representatives, args.relevance_batch_size)
        av_count = 0
        for batch_index, batch in enumerate(batches, start=1):
            jobs_by_id = {}
            for job_id, posting in batch:
                title = normalize_text(_resolve(posting, aliases, "title"))
                description = _relevance_input(posting, aliases, args.relevance_max_description_chars)
                jobs_by_id[job_id] = {"id": job_id, "title": title, "description": description}
            results = cls._classify_with_retry(classifier, jobs_by_id, batch_index, len(batches))

            for rep_id, _rep_posting in batch:
                decision = results.get(rep_id)
                for job_id in dedup_map.get(rep_id, [rep_id]):
                    posting = postings_by_id[job_id]
                    if decision is None:
                        _write_line(
                            failed_file,
                            {**posting, "_job_id": job_id, "_error": "no usable relevance decision after retry"},
                        )
                        continue
                    record = {**posting, "_job_id": job_id, "_classification": classification_as_dict(decision)}
                    if decision.is_av_relevant:
                        _write_line(av_candidates_file, record)
                        av_count += 1
                    else:
                        _write_line(non_av_file, record)

            logger.info(
                "relevance batch %d/%d done; av_candidates so far=%d",
                batch_index,
                len(batches),
                av_count,
            )
            cls._write_metrics(paths, total, skipped_count)
        return av_count

    @staticmethod
    def _classify_with_retry(classifier, jobs_by_id: dict, batch_index: int, total_batches: int) -> dict:
        try:
            results = classifier.classify_batch(list(jobs_by_id.values()))
        except Exception as exc:  # noqa: BLE001 - isolate one bad batch from the whole run
            logger.error(
                "relevance batch %d/%d (%d jobs) failed outright: %s",
                batch_index,
                total_batches,
                len(jobs_by_id),
                exc,
            )
            return {}

        missing_ids = set(jobs_by_id) - results.keys()
        if not missing_ids:
            return results

        # A group retry only helps when it's actually a *smaller* request
        # than the one that just failed - at temperature=0 an unchanged
        # (100%-missing) request reliably reproduces the same truncation, so
        # skip straight to individual retries in that case instead of
        # wasting a full pacing cycle re-sending an identical batch.
        still_missing = set(missing_ids)
        if len(missing_ids) < len(jobs_by_id):
            logger.warning(
                "relevance batch %d/%d: %d/%d jobs missing from response (likely truncated), retrying as a smaller group",
                batch_index,
                total_batches,
                len(missing_ids),
                len(jobs_by_id),
            )
            try:
                results.update(classifier.classify_batch([jobs_by_id[job_id] for job_id in missing_ids]))
            except Exception as exc:  # noqa: BLE001 - fall through to individual retry below
                logger.error("relevance group retry (%d jobs) failed: %s", len(missing_ids), exc)
            still_missing = set(jobs_by_id) - results.keys()

        if not still_missing:
            return results

        # A smaller group retry costs one request instead of re-paying the
        # fixed prompt overhead per job; only fall back to one-by-one for
        # whatever's still stubborn after that, so a handful of persistently
        # truncated jobs can't turn into a request storm.
        logger.warning(
            "relevance batch %d/%d: %d jobs still missing (group retry %s), retrying individually",
            batch_index,
            total_batches,
            len(still_missing),
            "skipped - same size as original batch" if len(missing_ids) == len(jobs_by_id) else "attempted",
        )
        for job_id in still_missing:
            try:
                results.update(classifier.classify_batch([jobs_by_id[job_id]]))
            except Exception as exc:  # noqa: BLE001 - a single stubborn job shouldn't stop the run
                logger.error("relevance retry for job=%s failed: %s", job_id, exc)
        return results

    @staticmethod
    def _write_metrics(paths: dict[str, Path], total: int, skipped_count: int) -> dict:
        summary = {
            "total": total,
            "av_candidates": _count_lines(paths["av_candidates"]),
            "non_av_count": _count_lines(paths["non_av"]),
            "failed_count": _count_lines(paths["failed"]),
            "skipped_already_processed": skipped_count,
        }
        JobPostingIO.write_json(paths["metrics"], summary)
        return summary


if __name__ == "__main__":
    raise SystemExit(JobClassifierMain.main())
