from __future__ import annotations

import json
import logging
from pathlib import Path

from scrapers.service.llm import JobEnricher, JobFilterConfig, JobPostingIO, classification_as_dict
from scrapers.service.llm.groq_client import GroqCompletion
from scrapers.service.llm.text import compress_job_text
from scrapers.utils.job_classifier import _chunk, _count_lines, _group_by_company_title, _load_processed_ids, _resolve, _write_line
from scrapers.utils.parser import ScraperParser

logger = logging.getLogger(__name__)


class JobEnricherMain:
    """Category and skill extraction (stage 2), resumable across interrupted runs.

    Reads whatever job_classifier.py (or relevance_classifier_cli.py's
    classifier-scored/LLM-corrected output) has accumulated in
    av_candidates.jsonl - this stage doesn't care whether a job's AV-relevant
    decision came from the LLM directly or from the distilled classifier,
    only that it's marked AV-relevant. Exact (company, title) duplicates are
    enriched once and the result fanned out to every repost.
    """

    @classmethod
    def main(cls, argv: list[str] | None = None) -> int:
        args = ScraperParser.parse_job_enricher_args(argv)
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )

        aliases = JobFilterConfig.load().field_aliases
        enricher = JobEnricher(GroqCompletion())

        output_dir = args.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        paths = {
            "av": output_dir / "av_jobs.jsonl",
            "failed": output_dir / "failed_jobs.jsonl",
            "metrics": output_dir / "enrichment_metrics.json",
        }

        processed_ids = _load_processed_ids(paths["av"]) | _load_processed_ids(paths["failed"])
        if processed_ids:
            logger.info("Resuming: %d jobs already enriched, skipping them.", len(processed_ids))

        candidates = JobPostingIO.load(args.input)
        total = len(candidates)

        pending = []
        decisions_by_id: dict[str, dict] = {}
        postings_by_id: dict[str, dict] = {}
        for record in candidates:
            job_id = record.get("_job_id") or _resolve(record, aliases, "id") or "unknown"
            postings_by_id[job_id] = record
            decisions_by_id[job_id] = record.get("_classification", {})
            if job_id in processed_ids:
                continue
            pending.append((job_id, record))

        skipped_count = total - len(pending)
        representatives, dedup_map = _group_by_company_title(pending, aliases)
        if len(representatives) < len(pending):
            logger.info(
                "Deduped %d AV candidates to %d unique (company, title) groups.", len(pending), len(representatives)
            )

        with paths["av"].open("a", encoding="utf-8") as av_file, paths["failed"].open(
            "a", encoding="utf-8"
        ) as failed_file:
            category_counts = cls._run_enrichment_stage(
                enricher,
                aliases,
                representatives,
                dedup_map,
                postings_by_id,
                decisions_by_id,
                args,
                av_file,
                failed_file,
                paths,
                total,
                skipped_count,
            )

        summary = cls._write_metrics(paths, total, skipped_count, category_counts)
        print(json.dumps({**summary, "outputs": {name: str(path) for name, path in paths.items()}}, indent=2))
        return 0

    @classmethod
    def _run_enrichment_stage(
        cls,
        enricher,
        aliases,
        representatives,
        dedup_map,
        postings_by_id,
        decisions_by_id,
        args,
        av_file,
        failed_file,
        paths,
        total,
        skipped_count,
    ) -> dict[str, int]:
        batches = _chunk(representatives, args.batch_size)
        category_counts: dict[str, int] = {}
        for batch_index, batch in enumerate(batches, start=1):
            jobs_by_id = {}
            for job_id, posting in batch:
                title, description = compress_job_text(
                    _resolve(posting, aliases, "title"),
                    _resolve(posting, aliases, "description"),
                    args.max_description_chars,
                )
                jobs_by_id[job_id] = {"id": job_id, "title": title, "description": description}
            results = cls._enrich_with_retry(enricher, jobs_by_id, batch_index, len(batches))

            for rep_id, _rep_posting in batch:
                enrichment = results.get(rep_id)
                for job_id in dedup_map.get(rep_id, [rep_id]):
                    posting = postings_by_id[job_id]
                    relevance = decisions_by_id.get(job_id, {})
                    if enrichment is None:
                        _write_line(
                            failed_file,
                            {**posting, "_job_id": job_id, "_error": "no usable enrichment after retry"},
                        )
                        continue
                    merged = {
                        **relevance,
                        "categories": list(enrichment.categories),
                        "skills": [{"name": s.name, "skill_type": s.skill_type} for s in enrichment.skills],
                    }
                    _write_line(av_file, {**posting, "_job_id": job_id, "_classification": merged})
                    for category in enrichment.categories:
                        category_counts[category] = category_counts.get(category, 0) + 1

            logger.info("enrichment batch %d/%d done", batch_index, len(batches))
            cls._write_metrics(paths, total, skipped_count, category_counts)
        return category_counts

    @staticmethod
    def _enrich_with_retry(enricher, jobs_by_id: dict, batch_index: int, total_batches: int) -> dict:
        try:
            results = enricher.enrich_batch(list(jobs_by_id.values()))
        except Exception as exc:  # noqa: BLE001 - isolate one bad batch from the whole run
            logger.error(
                "enrichment batch %d/%d (%d jobs) failed outright: %s",
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
                "enrichment batch %d/%d: %d/%d jobs missing from response (likely truncated), retrying as a smaller group",
                batch_index,
                total_batches,
                len(missing_ids),
                len(jobs_by_id),
            )
            try:
                results.update(enricher.enrich_batch([jobs_by_id[job_id] for job_id in missing_ids]))
            except Exception as exc:  # noqa: BLE001 - fall through to individual retry below
                logger.error("enrichment group retry (%d jobs) failed: %s", len(missing_ids), exc)
            still_missing = set(jobs_by_id) - results.keys()

        if not still_missing:
            return results

        # A smaller group retry costs one request instead of re-paying the
        # ~850-token taxonomy prompt per job; only fall back to one-by-one
        # for whatever's still stubborn after that, so a handful of
        # persistently truncated jobs can't turn into a request storm.
        logger.warning(
            "enrichment batch %d/%d: %d jobs still missing (group retry %s), retrying individually",
            batch_index,
            total_batches,
            len(still_missing),
            "skipped - same size as original batch" if len(missing_ids) == len(jobs_by_id) else "attempted",
        )
        for job_id in still_missing:
            try:
                results.update(enricher.enrich_batch([jobs_by_id[job_id]]))
            except Exception as exc:  # noqa: BLE001 - a single stubborn job shouldn't stop the run
                logger.error("enrichment retry for job=%s failed: %s", job_id, exc)
        return results

    @staticmethod
    def _write_metrics(paths: dict[str, Path], total: int, skipped_count: int, category_counts: dict) -> dict:
        summary = {
            "total": total,
            "av_count": _count_lines(paths["av"]),
            "failed_count": _count_lines(paths["failed"]),
            "skipped_already_processed": skipped_count,
            "category_counts": category_counts,
        }
        JobPostingIO.write_json(paths["metrics"], summary)
        return summary


if __name__ == "__main__":
    raise SystemExit(JobEnricherMain.main())
