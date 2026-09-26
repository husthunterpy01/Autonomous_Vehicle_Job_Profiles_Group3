import json
from pathlib import Path
from unittest.mock import patch

import scrapers.utils.job_enricher as job_enricher_module
from scrapers.service.llm.job_enricher import JobEnrichment
from scrapers.utils.job_enricher import JobEnricherMain


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row) + "\n")


def _run(tmp_path: Path, candidates: list[dict], enricher_cls):
    input_path = tmp_path / "av_candidates.jsonl"
    _write_jsonl(input_path, candidates)
    output_dir = tmp_path / "out"
    with patch.object(job_enricher_module, "JobEnricher", enricher_cls), patch.object(
        job_enricher_module, "GroqCompletion", lambda: None
    ):
        JobEnricherMain.main(["--input", str(input_path), "--output-dir", str(output_dir)])
    return output_dir


class _EchoEnricher:
    """Returns one enrichment per job id it actually received."""

    def __init__(self, *_args, **_kwargs):
        pass

    def enrich_batch(self, jobs):
        return {job["id"]: JobEnrichment(categories=("Perception",), skills=()) for job in jobs}


def test_cross_company_source_job_id_collision_no_longer_drops_a_posting(tmp_path):
    # Regression test: two unrelated jobs at different companies sharing a
    # small numeric source_job_id (plausible with Greenhouse/SmartRecruiters
    # ids or Workday requisition numbers) must both survive, keyed on their
    # distinct deduplication_key instead of the colliding source_job_id.
    candidates = [
        {
            "source_job_id": "42",
            "deduplication_key": "dedupA",
            "company_name": "Company A",
            "job_title": "Perception Engineer",
            "job_description": "A" * 500,
            "_classification": {"relevant": True},
        },
        {
            "source_job_id": "42",
            "deduplication_key": "dedupB",
            "company_name": "Company B",
            "job_title": "Planning Engineer",
            "job_description": "B" * 500,
            "_classification": {"relevant": True},
        },
    ]

    output_dir = _run(tmp_path, candidates, _EchoEnricher)

    av_lines = (output_dir / "av_jobs.jsonl").read_text().splitlines()
    companies = {json.loads(line)["company_name"] for line in av_lines}

    assert len(av_lines) == 2
    assert companies == {"Company A", "Company B"}

    metrics = json.loads((output_dir / "enrichment_metrics.json").read_text())
    assert metrics["total"] == 2
    assert metrics["av_count"] == 2


class _RaisesOnceThenWorks:
    """Simulates a transient batch-level failure (5xx / connection error /
    empty completion / truncated JSON) on the very first call only."""

    calls = 0

    def __init__(self, *_args, **_kwargs):
        pass

    def enrich_batch(self, jobs):
        type(self).calls += 1
        if type(self).calls == 1:
            raise ConnectionError("simulated transient failure")
        return {job["id"]: JobEnrichment(categories=("Perception",), skills=()) for job in jobs}


def test_transient_batch_failure_recovers_via_individual_retry_instead_of_failing_everyone(tmp_path):
    # Regression test: a single Groq 5xx/connection error must not mark
    # every job in the batch permanently failed - it should fall through to
    # individual retries, same as a partially-truncated response would.
    _RaisesOnceThenWorks.calls = 0
    candidates = [
        {
            "deduplication_key": "j1",
            "company_name": "Company A",
            "job_title": "Perception Engineer",
            "job_description": "A" * 500,
            "_classification": {"relevant": True},
        },
        {
            "deduplication_key": "j2",
            "company_name": "Company C",
            "job_title": "Planning Engineer",
            "job_description": "C" * 500,
            "_classification": {"relevant": True},
        },
    ]

    output_dir = _run(tmp_path, candidates, _RaisesOnceThenWorks)

    assert len((output_dir / "av_jobs.jsonl").read_text().splitlines()) == 2
    assert (output_dir / "enrichment_failed_jobs.jsonl").read_text() == ""


class _AlwaysRaises:
    def __init__(self, *_args, **_kwargs):
        pass

    def enrich_batch(self, jobs):
        raise ConnectionError("simulated persistent failure")


def test_persistent_batch_failure_still_lands_in_failed_jobs_after_individual_retries_exhausted(tmp_path):
    # A genuinely unrecoverable failure (every individual retry also fails)
    # should still end up in failed_jobs.jsonl - only the "one flaky call
    # blacklists everyone" behavior was the bug.
    candidates = [
        {
            "deduplication_key": "j1",
            "company_name": "Company A",
            "job_title": "Perception Engineer",
            "job_description": "A" * 500,
            "_classification": {"relevant": True},
        },
    ]

    output_dir = _run(tmp_path, candidates, _AlwaysRaises)

    assert (output_dir / "av_jobs.jsonl").read_text() == ""
    assert len((output_dir / "enrichment_failed_jobs.jsonl").read_text().splitlines()) == 1


class _ExplodingEnricher:
    """Fails the test immediately if the LLM enrichment path is ever
    reached - used to prove a job was resolved by the keyword pass alone."""

    def __init__(self, *_args, **_kwargs):
        pass

    def enrich_batch(self, jobs):
        raise AssertionError(f"LLM enrichment should not have been called for {jobs}")


def test_keyword_resolvable_job_never_reaches_the_llm(tmp_path):
    # Regression test: KeywordCategoryClassifier existed but nothing in the
    # pipeline called it, so every job - even ones its curated vocabulary
    # covers - went through Groq. A job whose TITLE matches a known category
    # keyword should now be resolved by the keyword pass alone. The title
    # must be the one carrying the match: KeywordCategoryClassifier no
    # longer trusts a description-only match once a title is supplied (see
    # its own docstring) - a company's boilerplate "about us" paragraph
    # regularly lists unrelated departments ("...cloud platforms, mapping,
    # sensors...") and a bare word like "mapping" in that list previously
    # keyword-matched real jobs (a cybersecurity engineer, several vehicle
    # test operators) to the wrong category with no LLM involved. Bare
    # "Perception" is deliberately not a keyword (Perception is not "the ML
    # category" - see categories_definition.txt), so the title here names
    # the specific keyword phrase instead.
    candidates = [
        {
            "deduplication_key": "j1",
            "company_name": "Company A",
            "job_title": "Object Detection Engineer",
            "job_description": "We build object detection and object tracking pipelines using LiDAR.",
            "_classification": {"relevant": True},
        },
    ]

    output_dir = _run(tmp_path, candidates, _ExplodingEnricher)

    av_lines = (output_dir / "av_jobs.jsonl").read_text().splitlines()
    assert len(av_lines) == 1
    record = json.loads(av_lines[0])
    assert "Perception" in record["_classification"]["categories"]
    assert record["_classification"]["category_source"] == "keyword_resolved"

    metrics = json.loads((output_dir / "enrichment_metrics.json").read_text())
    assert metrics["keyword_resolved"] == 1
    assert metrics["llm_enriched"] == 0


def test_keyword_unresolvable_job_falls_back_to_the_llm(tmp_path):
    # A description matching none of the categories' keywords must still
    # fall back to Groq, per KeywordCategoryClassifier's own documented
    # contract (empty result = "not covered, ask the LLM").
    candidates = [
        {
            "deduplication_key": "j1",
            "company_name": "Company A",
            "job_title": "Vague Role",
            "job_description": "General AV-adjacent responsibilities, details TBD.",
            "_classification": {"relevant": True},
        },
    ]

    output_dir = _run(tmp_path, candidates, _EchoEnricher)

    av_lines = (output_dir / "av_jobs.jsonl").read_text().splitlines()
    assert len(av_lines) == 1
    record = json.loads(av_lines[0])
    assert record["_classification"]["category_source"] == "llm_enriched"

    metrics = json.loads((output_dir / "enrichment_metrics.json").read_text())
    assert metrics["keyword_resolved"] == 0
    assert metrics["llm_enriched"] == 1


def test_mixed_batch_splits_between_keyword_and_llm_resolution(tmp_path):
    candidates = [
        {
            "deduplication_key": "j1",
            "company_name": "Company A",
            "job_title": "Object Detection Engineer",
            "job_description": "We build object detection and object tracking pipelines using LiDAR.",
            "_classification": {"relevant": True},
        },
        {
            "deduplication_key": "j2",
            "company_name": "Company B",
            "job_title": "Vague Role",
            "job_description": "General AV-adjacent responsibilities, details TBD.",
            "_classification": {"relevant": True},
        },
    ]

    output_dir = _run(tmp_path, candidates, _EchoEnricher)

    av_lines = (output_dir / "av_jobs.jsonl").read_text().splitlines()
    sources_by_company = {json.loads(line)["company_name"]: json.loads(line)["_classification"]["category_source"] for line in av_lines}
    assert sources_by_company == {"Company A": "keyword_resolved", "Company B": "llm_enriched"}

    metrics = json.loads((output_dir / "enrichment_metrics.json").read_text())
    assert metrics["keyword_resolved"] == 1
    assert metrics["llm_enriched"] == 1


class _NoFitEnricher:
    """Finds no category for titles containing "Business Systems", one for the rest."""

    def __init__(self, *_args, **_kwargs):
        pass

    def enrich_batch(self, jobs):
        return {
            job["id"]: JobEnrichment(
                categories=() if "Business Systems" in job["title"] else ("Perception",), skills=()
            )
            for job in jobs
        }


def test_job_with_no_fitting_category_is_dropped_not_given_a_fallback_category(tmp_path):
    candidates = [
        {
            "deduplication_key": "fits",
            "company_name": "Company A",
            "job_title": "Vague Role",
            "job_description": "General AV-adjacent responsibilities, details TBD.",
            "_classification": {"relevant": True},
        },
        {
            "deduplication_key": "nofit",
            "company_name": "Company A",
            "job_title": "Business Systems Engineer",
            "job_description": "NetSuite and Workday integrations for finance and HR.",
            "_classification": {"relevant": True},
        },
    ]

    output_dir = _run(tmp_path, candidates, _NoFitEnricher)

    av = [json.loads(line) for line in (output_dir / "av_jobs.jsonl").read_text().splitlines()]
    assert [r["deduplication_key"] for r in av] == ["fits"]

    dropped = [json.loads(line) for line in (output_dir / "no_category_jobs.jsonl").read_text().splitlines()]
    assert [r["deduplication_key"] for r in dropped] == ["nofit"]
    assert dropped[0]["_classification"]["categories"] == []
    assert dropped[0]["_classification"]["is_av_relevant"] == "False"

    metrics = json.loads((output_dir / "enrichment_metrics.json").read_text())
    assert metrics["av_count"] == 1
    assert metrics["no_category_count"] == 1
    assert metrics["failed_count"] == 0
