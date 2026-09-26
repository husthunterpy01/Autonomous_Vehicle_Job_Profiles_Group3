from __future__ import annotations

import json
import logging

from scrapers.service.llm import (
    AVFunctionFilter,
    JobFilterConfig,
    JobPostingIO,
    title_flags_review,
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


class AVFunctionFilterMain:
    """Job-function filter, run between AV-relevance screening
    (job_classifier.py) and category/skill enrichment (job_enricher.py).

    This project tracks AV ENGINEERING skills demand - job_classifier.py
    already screens out jobs that aren't about AV technology at all, but it
    has no opinion on job *function*: a "Technical Program Manager,
    Simulation" or "Product Manager, Autonomous Driving" is genuinely
    AV-relevant and passes that screen easily, yet isn't an engineering role
    this project should track. Before this stage existed, jobs like that had
    nowhere real to land and silently piled up in whichever category read
    closest to their (often generic) title or company-boilerplate text -
    Infrastructure absorbed the worst of it, since "platform"/"tooling"
    language shows up in both genuinely technical roles and in program
    management ones. See the Infrastructure-category audit this stage
    formalizes: of 866 jobs sampled by title pattern, 110 (12.7%) were
    flagged - 68 non-engineering functions and 42 real engineering roles
    miscategorized for unrelated reasons.

    Cheap by design: title_flags_review() is a broad-recall, zero-cost
    pre-filter - only jobs whose title matches a non-engineering-function
    signal (Product Manager, TPM, Sourcer, Operations Coordinator, Policy
    Advisor, Account Manager, etc.) are sent to the LLM at all. Everything
    else passes straight through with no Groq call. The regex only decides
    which jobs get a closer look; per the lesson this stage exists to fix,
    it never decides the outcome by itself - AVFunctionFilter always reads
    the full description before a job is excluded, exactly the same
    title-decides-candidacy-but-content-decides-outcome split job_enricher.py
    already uses for categories.

    Resumable across interrupted runs, same as job_classifier.py and
    job_enricher.py: engineering.jsonl and non_engineering_jobs.jsonl are
    durable, appended-to output, not just an in-memory pass/fail list.
    """

    @classmethod
    def main(cls, argv: list[str] | None = None) -> int:
        args = ScraperParser.parse_av_function_filter_args(argv)
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )

        aliases = JobFilterConfig.load().field_aliases
        function_filter = AVFunctionFilter(GroqCompletion())

        output_dir = args.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        paths = {
            "engineering": output_dir / "av_engineering_candidates.jsonl",
            "non_engineering": output_dir / "non_engineering_jobs.jsonl",
            "failed": output_dir / "function_filter_failed_jobs.jsonl",
            "metrics": output_dir / "function_filter_metrics.json",
        }

        processed_ids = (
            _load_processed_ids(paths["engineering"])
            | _load_processed_ids(paths["non_engineering"])
            | _load_processed_ids(paths["failed"])
        )
        if processed_ids:
            logger.info("Resuming: %d jobs already function-filtered, skipping them.", len(processed_ids))

        counts = {
            "engineering": _count_lines(paths["engineering"]),
            "non_engineering": _count_lines(paths["non_engineering"]),
            "failed": _count_lines(paths["failed"]),
            "passed_through": 0,
            "llm_confirmed_engineering": 0,
        }

        candidates = JobPostingIO.load(args.input)
        total = len(candidates)

        pending = []
        postings_by_id: dict[str, dict] = {}
        for record in candidates:
            job_id = record.get("_job_id") or _job_key(record, aliases)
            postings_by_id[job_id] = record
            if job_id in processed_ids:
                continue
            pending.append((job_id, record))

        skipped_count = total - len(pending)
        representatives, dedup_map = _group_by_company_title(pending, aliases)
        if len(representatives) < len(pending):
            logger.info(
                "Deduped %d pending jobs to %d unique (company, title) groups.", len(pending), len(representatives)
            )

        with paths["engineering"].open("a", encoding="utf-8") as engineering_file, paths[
            "non_engineering"
        ].open("a", encoding="utf-8") as non_engineering_file, paths["failed"].open(
            "a", encoding="utf-8"
        ) as failed_file:
            cls._run_function_filter_stage(
                function_filter,
                aliases,
                representatives,
                dedup_map,
                postings_by_id,
                args,
                engineering_file,
                non_engineering_file,
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
    def _run_function_filter_stage(
        cls,
        function_filter,
        aliases,
        representatives,
        dedup_map,
        postings_by_id,
        args,
        engineering_file,
        non_engineering_file,
        failed_file,
        paths,
        total,
        skipped_count,
        counts: dict[str, int],
    ) -> None:
        needs_llm = []
        for rep_id, posting in representatives:
            title = _resolve(posting, aliases, "title")
            if title_flags_review(title):
                needs_llm.append((rep_id, posting))
                continue
            cls._write_result(
                rep_id, None, "passed_through", dedup_map, postings_by_id,
                engineering_file, non_engineering_file, failed_file, counts,
            )

        if representatives:
            logger.info(
                "Title pre-filter: %d/%d representative groups need an LLM function check.",
                len(needs_llm), len(representatives),
            )
        cls._write_metrics(paths, total, skipped_count, counts)

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
            results = cls._classify_with_retry(function_filter, jobs_by_id, batch_index, len(batches))

            for rep_id, _rep_posting in batch:
                decision = results.get(rep_id)
                source = "llm_confirmed_engineering" if decision and decision.is_engineering_role else "non_engineering"
                cls._write_result(
                    rep_id, decision, source, dedup_map, postings_by_id,
                    engineering_file, non_engineering_file, failed_file, counts,
                )

            logger.info(
                "function-filter batch %d/%d done; non_engineering so far=%d",
                batch_index, len(batches), counts["non_engineering"],
            )
            cls._write_metrics(paths, total, skipped_count, counts)

    @staticmethod
    def _write_result(
        rep_id, decision, source, dedup_map, postings_by_id,
        engineering_file, non_engineering_file, failed_file, counts,
    ) -> None:
        for job_id in dedup_map.get(rep_id, [rep_id]):
            posting = postings_by_id[job_id]
            if source == "passed_through":
                _write_line(engineering_file, {**posting, "_job_id": job_id})
                counts["engineering"] += 1
                counts["passed_through"] += 1
                continue
            if decision is None:
                _write_line(
                    failed_file,
                    {**posting, "_job_id": job_id, "_error": "no usable function decision after retry"},
                )
                counts["failed"] += 1
                continue
            record = {
                **posting,
                "_job_id": job_id,
                "_function_filter": {
                    "is_engineering_role": decision.is_engineering_role,
                    "confidence": decision.confidence,
                    "reason": decision.reason,
                },
            }
            if decision.is_engineering_role:
                _write_line(engineering_file, record)
                counts["engineering"] += 1
                counts["llm_confirmed_engineering"] += 1
            else:
                _write_line(non_engineering_file, record)
                counts["non_engineering"] += 1

    @staticmethod
    def _classify_with_retry(function_filter, jobs_by_id: dict, batch_index: int, total_batches: int) -> dict:
        return _batch_call_with_retry(
            function_filter.classify_batch, jobs_by_id, batch_index, total_batches, label="function-filter"
        )

    @staticmethod
    def _write_metrics(paths, total: int, skipped_count: int, counts: dict[str, int]) -> dict:
        summary = {
            "total": total,
            "engineering_count": counts["engineering"],
            "non_engineering_count": counts["non_engineering"],
            "failed_count": counts["failed"],
            "passed_through_count": counts["passed_through"],
            "llm_confirmed_engineering_count": counts["llm_confirmed_engineering"],
            "skipped_already_processed": skipped_count,
        }
        JobPostingIO.write_json(paths["metrics"], summary)
        return summary


if __name__ == "__main__":
    raise SystemExit(AVFunctionFilterMain.main())
