from __future__ import annotations

import json
import logging
from pathlib import Path

from scrapers.service.llm import (
    JobEnricher,
    JobEnrichment,
    JobFilterConfig,
    JobPostingIO,
    KeywordCategoryClassifier,
    KeywordSkillExtractor,
)
from scrapers.service.llm.groq_client import GroqCompletion
from scrapers.service.llm.text import compress_job_text
from scrapers.utils.job_classifier import (
    _batch_call_with_retry,
    _chunk,
    _count_lines,
    _group_by_company_title,
    _job_key,
    _load_processed_ids,
    _resolve,
    _write_line,
)
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

    Before paying for a Groq call, every representative group is first run
    through KeywordCategoryClassifier - deterministic, zero-LLM category
    matching against the same curated vocabulary the LLM prompt itself uses
    (categories_definition.txt). Per its own documented contract, an empty
    result means "not covered by this vocabulary" and falls back to Groq;
    anything else is accepted as-is (plus KeywordSkillExtractor for skills)
    without ever calling the LLM for that job. This is what keeps
    "keyword-resolved" vs "llm_enriched" in enrichment_metrics.json
    meaningful rather than the keyword classifier just being dead code.
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
        keyword_classifier = KeywordCategoryClassifier()
        keyword_skill_extractor = KeywordSkillExtractor()

        output_dir = args.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        paths = {
            "av": output_dir / "av_jobs.jsonl",
            # Stage-specific filename - see the matching comment in
            # job_classifier.py for why this can't share "failed_jobs.jsonl"
            # with the relevance stage even though they share output_dir.
            "failed": output_dir / "enrichment_failed_jobs.jsonl",
            # Jobs the enricher explicitly found no category for. There is
            # no fallback category by design: a role that fits none of the
            # taxonomy is treated as not AV engineering and kept out of
            # av_jobs.jsonl (its own file, not non_av_jobs.jsonl, so the
            # relevance stage's resume logic never sees these ids).
            "no_category": output_dir / "no_category_jobs.jsonl",
            "metrics": output_dir / "enrichment_metrics.json",
        }

        processed_ids = (
            _load_processed_ids(paths["av"])
            | _load_processed_ids(paths["failed"])
            | _load_processed_ids(paths["no_category"])
        )
        if processed_ids:
            logger.info("Resuming: %d jobs already enriched, skipping them.", len(processed_ids))

        # Read once here (a resumed run may already have content in these
        # files) and kept up to date in memory from here on - re-reading
        # every output file in full after every batch (the old
        # _write_metrics behavior) turned a long run's progress logging into
        # its own O(n^2) cost as the files grew.
        counts = {
            "av": _count_lines(paths["av"]),
            "failed": _count_lines(paths["failed"]),
            "no_category": _count_lines(paths["no_category"]),
            # Only cover this run's own work (not re-derived from prior runs'
            # output on resume) - see the metrics docstring note below.
            "keyword_resolved": 0,
            "llm_enriched": 0,
        }

        candidates = JobPostingIO.load(args.input)
        total = len(candidates)

        pending = []
        decisions_by_id: dict[str, dict] = {}
        postings_by_id: dict[str, dict] = {}
        for record in candidates:
            job_id = record.get("_job_id") or _job_key(record, aliases)
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
        ) as failed_file, paths["no_category"].open("a", encoding="utf-8") as no_category_file:
            category_counts = cls._run_enrichment_stage(
                enricher,
                keyword_classifier,
                keyword_skill_extractor,
                aliases,
                representatives,
                dedup_map,
                postings_by_id,
                decisions_by_id,
                args,
                av_file,
                failed_file,
                no_category_file,
                paths,
                total,
                skipped_count,
                counts,
            )

        summary = cls._write_metrics(paths, total, skipped_count, category_counts, counts)
        print(json.dumps({**summary, "outputs": {name: str(path) for name, path in paths.items()}}, indent=2))
        return 0

    @classmethod
    def _run_enrichment_stage(
        cls,
        enricher,
        keyword_classifier,
        keyword_skill_extractor,
        aliases,
        representatives,
        dedup_map,
        postings_by_id,
        decisions_by_id,
        args,
        av_file,
        failed_file,
        no_category_file,
        paths,
        total,
        skipped_count,
        counts: dict[str, int],
    ) -> dict[str, int]:
        category_counts: dict[str, int] = {}

        # Pass 1: resolve via the deterministic keyword classifier wherever
        # its curated vocabulary covers this job - free, instant, and no
        # Groq budget spent. Anything it can't categorize (empty result, by
        # its own documented contract) is deferred to pass 2.
        needs_llm = []
        for rep_id, posting in representatives:
            title, description = compress_job_text(
                _resolve(posting, aliases, "title"),
                _resolve(posting, aliases, "description"),
                args.max_description_chars,
            )
            categories = keyword_classifier.classify(f"{title} {description}", title=title)
            if not categories:
                needs_llm.append((rep_id, posting))
                continue
            skills = keyword_skill_extractor.extract(f"{title} {description}")
            enrichment = JobEnrichment(categories=categories, skills=skills)
            cls._write_enrichment_result(
                rep_id, enrichment, "keyword_resolved", dedup_map, postings_by_id, decisions_by_id,
                av_file, failed_file, no_category_file, counts, category_counts,
            )

        if needs_llm:
            logger.info(
                "Keyword pass resolved %d/%d representative groups without an LLM call; %d need Groq.",
                len(representatives) - len(needs_llm), len(representatives), len(needs_llm),
            )
        elif representatives:
            logger.info("Keyword pass resolved all %d representative groups; no LLM calls needed.", len(representatives))
        if representatives:
            cls._write_metrics(paths, total, skipped_count, category_counts, counts)

        # Pass 2: whatever the keyword pass couldn't cover goes through Groq,
        # batched and retried exactly as before.
        batches = _chunk(needs_llm, args.batch_size)
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
                cls._write_enrichment_result(
                    rep_id, results.get(rep_id), "llm_enriched", dedup_map, postings_by_id, decisions_by_id,
                    av_file, failed_file, no_category_file, counts, category_counts,
                )

            logger.info("enrichment batch %d/%d done", batch_index, len(batches))
            cls._write_metrics(paths, total, skipped_count, category_counts, counts)
        return category_counts

    @staticmethod
    def _write_enrichment_result(
        rep_id, enrichment, source, dedup_map, postings_by_id, decisions_by_id, av_file, failed_file, no_category_file,
        counts, category_counts,
    ) -> None:
        """Fan a representative's enrichment result (or failure) out to every
        (company, title) duplicate it stands in for, tagging which of the
        two enrichment sources ("keyword_resolved" or "llm_enriched")
        produced it."""
        for job_id in dedup_map.get(rep_id, [rep_id]):
            posting = postings_by_id[job_id]
            relevance = decisions_by_id.get(job_id, {})
            if enrichment is None:
                _write_line(
                    failed_file,
                    {**posting, "_job_id": job_id, "_error": "no usable enrichment after retry"},
                )
                counts["failed"] += 1
                continue
            if not enrichment.categories:
                _write_line(
                    no_category_file,
                    {
                        **posting,
                        "_job_id": job_id,
                        "_classification": {
                            **relevance,
                            "is_av_relevant": "False",
                            "categories": [],
                            "category_source": source,
                            "_note": "No category in the taxonomy fits this role's responsibilities; "
                            "treated as not AV engineering (no fallback category).",
                        },
                    },
                )
                counts["no_category"] += 1
                continue
            merged = {
                **relevance,
                "categories": list(enrichment.categories),
                "skills": [{"name": s.name, "skill_type": s.skill_type} for s in enrichment.skills],
                "category_source": source,
                "category_area": enrichment.area,
                "category_evidence": enrichment.evidence,
            }
            _write_line(av_file, {**posting, "_job_id": job_id, "_classification": merged})
            counts["av"] += 1
            counts[source] += 1
            for category in enrichment.categories:
                category_counts[category] = category_counts.get(category, 0) + 1

    @staticmethod
    def _enrich_with_retry(enricher, jobs_by_id: dict, batch_index: int, total_batches: int) -> dict:
        return _batch_call_with_retry(
            enricher.enrich_batch, jobs_by_id, batch_index, total_batches, label="enrichment"
        )

    @staticmethod
    def _write_metrics(
        paths: dict[str, Path], total: int, skipped_count: int, category_counts: dict, counts: dict[str, int]
    ) -> dict:
        summary = {
            "total": total,
            "av_count": counts["av"],
            "failed_count": counts["failed"],
            "no_category_count": counts["no_category"],
            "skipped_already_processed": skipped_count,
            # This run's own split only - unlike av_count/failed_count, not
            # re-derived from prior runs' output on resume (would mean
            # re-reading every av_jobs.jsonl line's category_source, the
            # exact per-batch full-file re-read this refactor removed).
            "keyword_resolved": counts["keyword_resolved"],
            "llm_enriched": counts["llm_enriched"],
            "category_counts": category_counts,
        }
        JobPostingIO.write_json(paths["metrics"], summary)
        return summary


if __name__ == "__main__":
    raise SystemExit(JobEnricherMain.main())
