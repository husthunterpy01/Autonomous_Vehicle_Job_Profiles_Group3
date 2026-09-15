from __future__ import annotations

import json
import logging
import random
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

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


def _job_key(posting: Mapping[str, Any], aliases: Mapping[str, tuple[str, ...]]) -> str:
    """The stable identifier used to key/dedup postings internally.

    Deliberately not `_resolve(posting, aliases, "id")`: that alias chain
    (source_job_id, bronze_id, deduplication_key, id, job_id - see
    job_prefilter.yaml) exists for the prefilter's human-readable audit ID,
    where a per-company id like a Greenhouse/SmartRecruiters numeric id or a
    Workday requisition number is fine. It is not unique across companies,
    so using it to key postings_by_id let two unrelated jobs that happened
    to share a small numeric source_job_id silently collide - one dropped,
    the other double-written, with no error. deduplication_key (the Silver
    MD5 natural-key hash) is what the handoff and backend already treat as
    the real identity - use that first, and only fall back to the audit-id
    chain for the rare record that lacks it.
    """
    deduplication_key = posting.get("deduplication_key")
    if isinstance(deduplication_key, str) and deduplication_key.strip():
        return deduplication_key.strip()
    return _resolve(posting, aliases, "id") or "unknown"


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


def _batch_call_with_retry(
    call_batch: Callable[[list], dict],
    jobs_by_id: dict,
    batch_index: int,
    total_batches: int,
    *,
    label: str,
) -> dict:
    """Shared by JobClassifierMain and JobEnricherMain: both pass an LLM
    batch of jobs through a 3-tier retry (full batch -> group retry of the
    missing subset -> individual fallback) that only differs in which LLM
    call (`call_batch`) it's driving and what to call it in log messages."""
    try:
        results = call_batch(list(jobs_by_id.values()))
    except Exception as exc:  # noqa: BLE001 - isolate one bad batch from the whole run, not one bad job
        # A batch-level exception (5xx, connection error, empty completion,
        # truncated JSON the parser gave up on) is not evidence any
        # *individual* job in it is unrecoverable - treat it as "0 jobs came
        # back" so it falls into the same missing-id retry cascade below
        # (which, for a 100%-missing batch, already skips straight to
        # per-job retries) instead of marking every job in the batch
        # permanently failed after zero real attempts.
        logger.error(
            "%s batch %d/%d (%d jobs) failed outright: %s; retrying individually before giving up",
            label,
            batch_index,
            total_batches,
            len(jobs_by_id),
            exc,
        )
        results = {}

    missing_ids = set(jobs_by_id) - results.keys()
    if not missing_ids:
        return results

    # A group retry only helps when it's actually a *smaller* request than
    # the one that just failed - at temperature=0 an unchanged (100%-missing)
    # request reliably reproduces the same truncation, so skip straight to
    # individual retries in that case instead of wasting a full pacing cycle
    # re-sending an identical batch.
    still_missing = set(missing_ids)
    if len(missing_ids) < len(jobs_by_id):
        logger.warning(
            "%s batch %d/%d: %d/%d jobs missing from response (likely truncated), retrying as a smaller group",
            label,
            batch_index,
            total_batches,
            len(missing_ids),
            len(jobs_by_id),
        )
        try:
            results.update(call_batch([jobs_by_id[job_id] for job_id in missing_ids]))
        except Exception as exc:  # noqa: BLE001 - fall through to individual retry below
            logger.error("%s group retry (%d jobs) failed: %s", label, len(missing_ids), exc)
        still_missing = set(jobs_by_id) - results.keys()

    if not still_missing:
        return results

    # A smaller group retry costs one request instead of re-paying the fixed
    # prompt overhead per job; only fall back to one-by-one for whatever's
    # still stubborn after that, so a handful of persistently truncated jobs
    # can't turn into a request storm.
    logger.warning(
        "%s batch %d/%d: %d jobs still missing (group retry %s), retrying individually",
        label,
        batch_index,
        total_batches,
        len(still_missing),
        "skipped - same size as original batch" if len(missing_ids) == len(jobs_by_id) else "attempted",
    )
    for job_id in still_missing:
        try:
            results.update(call_batch([jobs_by_id[job_id]]))
        except Exception as exc:  # noqa: BLE001 - a single stubborn job shouldn't stop the run
            logger.error("%s retry for job=%s failed: %s", label, job_id, exc)
    return results


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
            # Stage-specific filename: job_enricher.py shares this same
            # output_dir (its input is this stage's av_candidates.jsonl), so
            # a shared "failed_jobs.jsonl" would let the two stages' failures
            # cross-contaminate each other's failed_count and, worse, resume
            # logic - a job that only failed enrichment would look like it
            # already failed relevance classification too.
            "failed": output_dir / "relevance_failed_jobs.jsonl",
            "metrics": output_dir / "relevance_metrics.json",
        }

        processed_ids = (
            _load_processed_ids(paths["av_candidates"])
            | _load_processed_ids(paths["non_av"])
            | _load_processed_ids(paths["failed"])
        )
        if processed_ids:
            logger.info("Resuming: %d jobs already classified, skipping them.", len(processed_ids))

        # Read once here (a resumed run may already have content in these
        # files) and kept up to date in memory from here on - re-reading
        # every output file in full after every batch (the old
        # _write_metrics behavior) turned a long run's progress logging into
        # its own O(n^2) cost as the files grew.
        counts = {
            "av_candidates": _count_lines(paths["av_candidates"]),
            "non_av": _count_lines(paths["non_av"]),
            "failed": _count_lines(paths["failed"]),
        }

        postings = JobPostingIO.load(args.input)
        total = len(postings)

        pending = []
        postings_by_id: dict[str, dict] = {}
        for posting in postings:
            job_id = _job_key(posting, aliases)
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
            cls._run_relevance_stage(
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
                counts,
            )

        summary = cls._write_metrics(paths, total, skipped_count, counts)
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
        counts: dict[str, int],
    ) -> int:
        batches = _chunk(representatives, args.relevance_batch_size)
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
                        counts["failed"] += 1
                        continue
                    record = {**posting, "_job_id": job_id, "_classification": classification_as_dict(decision)}
                    if decision.is_av_relevant:
                        _write_line(av_candidates_file, record)
                        counts["av_candidates"] += 1
                    else:
                        _write_line(non_av_file, record)
                        counts["non_av"] += 1

            logger.info(
                "relevance batch %d/%d done; av_candidates so far=%d",
                batch_index,
                len(batches),
                counts["av_candidates"],
            )
            cls._write_metrics(paths, total, skipped_count, counts)
        return counts["av_candidates"]

    @staticmethod
    def _classify_with_retry(classifier, jobs_by_id: dict, batch_index: int, total_batches: int) -> dict:
        return _batch_call_with_retry(
            classifier.classify_batch, jobs_by_id, batch_index, total_batches, label="relevance"
        )

    @staticmethod
    def _write_metrics(paths: dict[str, Path], total: int, skipped_count: int, counts: dict[str, int]) -> dict:
        summary = {
            "total": total,
            "av_candidates": counts["av_candidates"],
            "non_av_count": counts["non_av"],
            "failed_count": counts["failed"],
            "skipped_already_processed": skipped_count,
        }
        JobPostingIO.write_json(paths["metrics"], summary)
        return summary


if __name__ == "__main__":
    raise SystemExit(JobClassifierMain.main())
