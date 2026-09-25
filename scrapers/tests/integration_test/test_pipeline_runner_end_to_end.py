"""End-to-end coverage for scrapers.pipeline_main (PipelineRunner).

tests/unit_test/test_pipeline_runner.py mocks every stage class wholesale
and only checks that PipelineRunner calls them in the right order with the
right argv. It never proves the *real* stage classes actually hand each
other usable files. These tests wire the real classes together (JobPrefilter,
SilverExport, JobPrefilterMain, embedding relevance, JobEnricherMain, ...)
exactly as pipeline_main does, mocking the true external boundaries: the ATS
HTTP endpoints, MinIO, Postgres, and the `dbt` subprocess - the same
boundary the existing scraper integration test (test_scraper_pipeline.py)
mocks at. The one exception is JobClassifier/JobEnricher themselves (faked
with a simple classify_batch/enrich_batch, same pattern as
test_job_enricher_cli.py's _EchoEnricher): JobClassifier only runs when the
embedding probe puts jobs in the 0.45-0.55 mid-band.
"""

import json
from unittest.mock import MagicMock, patch

from scrapers.service.llm import ExtractedSkill, FunctionDecision, JobEnrichment, RelevanceDecision
from scrapers.utils.pipeline_runner import PipelineRunner


def _urlopen_json(payload):
    body = json.dumps(payload).encode("utf-8")
    mock_response = MagicMock()
    mock_response.read.return_value = body
    mock_response.status = 200
    mock_response.getcode.return_value = 200
    mock_response.headers = {"Content-Type": "application/json"}
    mock_response.__enter__.return_value = mock_response
    mock_response.__exit__.return_value = False
    return mock_response


def _stub_postgres(mock_connect):
    connection = mock_connect.return_value
    connection.cursor.return_value.__enter__.return_value = MagicMock()
    return connection


def _archive_minio_client(mock_minio, stored):
    stored.setdefault("objects", {})

    def put_object(**kwargs):
        payload = kwargs["data"].read()
        stored["object_name"] = kwargs["object_name"]
        stored["objects"][kwargs["object_name"]] = payload

    def list_objects(**_kwargs):
        objects = []
        for name in stored["objects"]:
            obj = MagicMock()
            obj.object_name = name
            objects.append(obj)
        return objects

    def get_object(_bucket, object_name):
        response = MagicMock()
        response.read.return_value = stored["objects"][object_name]
        return response

    client = mock_minio.return_value
    client.bucket_exists.return_value = False
    client.put_object.side_effect = put_object
    client.list_objects.side_effect = list_objects
    client.get_object.side_effect = get_object
    return client


def _stub_silver_export_rows(mock_connect, rows):
    """Wire scrapers.service.silver_cleaning.silver_export's psycopg2.connect
    mock to yield `rows` (plain dicts) from its `SELECT ... FROM
    silver.cleaned_job_postings` cursor, the same shape RealDictCursor gives."""
    connection = mock_connect.return_value
    cursor = MagicMock()
    cursor.__iter__.return_value = iter(rows)
    connection.cursor.return_value.__enter__.return_value = cursor
    return connection


# Fake JobClassifier/JobEnricher that answer directly from the job ids they
# actually received, instead of mocking GroqCompletion and round-tripping
# through real prompt-building + JSON response parsing. This mirrors the
# reviewed, CI-proven pattern in tests/unit_test/test_job_enricher_cli.py's
# _EchoEnricher: a GroqCompletion-level mock (fake `complete(prompt) -> str`,
# parsed back through the real JobClassifier/JobEnricher.parse_response) was
# tried here first and reliably passed 50+ local runs across multiple clean
# venvs and git worktrees, yet deterministically failed in CI in a way that
# resisted diagnosis even with call-by-call instrumentation - so this avoids
# that whole round trip rather than continuing to chase it blind.
class _FakeRelevanceClassifier:
    def __init__(self, *_args, **_kwargs):
        pass

    def classify_batch(self, jobs):
        return {job["id"]: RelevanceDecision(True, "High", ("autonomous vehicle",)) for job in jobs}


class _FakeEnricher:
    def __init__(self, *_args, **_kwargs):
        pass

    def enrich_batch(self, jobs):
        return {
            job["id"]: JobEnrichment(
                categories=("System and Safety",),
                skills=(ExtractedSkill(name="Program Management", skill_type="domain_concept"),),
            )
            for job in jobs
        }


# Every fixture job in this file is meant to reach enrichment (these tests
# are about the real Silver -> pre-filter -> relevance -> enrichment
# handoffs, not about which jobs the function filter excludes - that's
# covered by test_av_function_filter.py / test_av_function_filter_cli.py
# instead), so this always confirms "engineering" regardless of title,
# including the "AV Program Manager" fixture below (whose title genuinely
# matches the real title_flags_review() pre-filter and so is genuinely
# routed through this fake, exercising that code path for real).
class _FakeFunctionFilter:
    def __init__(self, *_args, **_kwargs):
        pass

    def classify_batch(self, jobs):
        return {job["id"]: FunctionDecision(True, "High", "test fixture") for job in jobs}


@patch("scrapers.utils.job_enricher.JobEnricher", _FakeEnricher)
@patch("scrapers.utils.job_enricher.GroqCompletion", lambda: None)
@patch("scrapers.utils.av_function_filter_cli.AVFunctionFilter", _FakeFunctionFilter)
@patch("scrapers.utils.av_function_filter_cli.GroqCompletion", lambda: None)
@patch("scrapers.utils.job_classifier.JobClassifier", _FakeRelevanceClassifier)
@patch("scrapers.utils.job_classifier.GroqCompletion", lambda: None)
@patch("scrapers.service.silver_cleaning.silver_export.psycopg2.connect")
@patch("scrapers.config.dbt.shutil.which", return_value="/usr/bin/dbt")
@patch("scrapers.config.dbt.subprocess.run")
@patch("scrapers.service.bronze_storage.bronze_ingest.execute_values")
@patch("scrapers.service.bronze_storage.bronze_ingest.psycopg2.connect")
@patch("scrapers.response_archive.Minio")
@patch("scrapers.service.fetch.rawfetch.urlopen")
def test_pipeline_runs_every_real_stage_and_hands_off_correct_files(
    mock_urlopen,
    mock_minio,
    mock_bronze_connect,
    mock_execute_values,
    mock_dbt_subprocess,
    _mock_which,
    mock_silver_connect,
    tmp_path,
):
    mock_urlopen.return_value = _urlopen_json(
        {"jobs": [{"id": "101", "title": "Software Engineer"}], "meta": {"total": 1}}
    )
    _archive_minio_client(mock_minio, {})
    _stub_postgres(mock_bronze_connect)
    mock_dbt_subprocess.return_value = MagicMock(returncode=0)

    # One job whose description matches the deterministic keyword taxonomy
    # (no LLM call needed for enrichment) and one that doesn't, so the run
    # exercises both of job_enricher.py's two passes for real.
    _stub_silver_export_rows(
        mock_silver_connect,
        [
            {
                "deduplication_key": "dk-perception-1",
                "company_name": "Stack AV",
                "job_name": "Object Detection Engineer",
                "job_description": (
                    "Build sensor fusion and computer vision pipelines for autonomous "
                    "vehicle perception, including lidar object detection."
                ),
            },
            {
                "deduplication_key": "dk-program-2",
                "company_name": "Waabi",
                "job_name": "AV Program Manager",
                "job_description": (
                    "Coordinate roadmap execution across engineering teams building the "
                    "autonomy product line, tracking milestones and dependencies."
                ),
            },
        ],
    )

    silver_export_path = tmp_path / "silver_export.jsonl"
    prefilter_output_dir = tmp_path / "job_prefilter"
    classification_output_dir = tmp_path / "job_classification"

    status = PipelineRunner.run(
        [
            "--company",
            "stack_av",
            "--silver-export-path",
            str(silver_export_path),
            "--prefilter-output-dir",
            str(prefilter_output_dir),
            "--classification-output-dir",
            str(classification_output_dir),
        ]
    )

    assert status == 0

    # Scrape -> bronze -> dbt Silver build all ran for real (against mocked
    # boundaries): dbt runs once for bronze's `+job_postings` and once for
    # the Silver stage's `+cleaned_job_postings`.
    mock_execute_values.assert_called_once()
    assert mock_dbt_subprocess.call_count == 2
    dbt_selects = [call.args[0][call.args[0].index("--select") + 1] for call in mock_dbt_subprocess.call_args_list]
    assert dbt_selects == ["+job_postings", "+cleaned_job_postings"]

    # Silver export -> pre-filter handoff: a real file on disk with both rows.
    assert silver_export_path.is_file()
    exported = [json.loads(line) for line in silver_export_path.read_text(encoding="utf-8").splitlines()]
    assert {row["deduplication_key"] for row in exported} == {"dk-perception-1", "dk-program-2"}

    # Pre-filter -> relevance handoff.
    llm_candidates_path = prefilter_output_dir / "llm_candidates.jsonl"
    assert llm_candidates_path.is_file()
    filter_metrics = json.loads((prefilter_output_dir / "filter_metrics.json").read_text(encoding="utf-8"))
    assert sum(company["before_count"] for company in filter_metrics) == 2
    assert sum(company["after_count"] for company in filter_metrics) == 2

    # Embedding relevance -> enrichment handoff. Both jobs scored as confident
    # AV, so Groq mid-band is skipped and relevance_metrics.json is not written.
    av_candidates_path = classification_output_dir / "av_candidates.jsonl"
    assert av_candidates_path.is_file()
    av_candidates = [
        json.loads(line)
        for line in av_candidates_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert {row["deduplication_key"] for row in av_candidates} == {"dk-perception-1", "dk-program-2"}
    assert all(row["_classification"]["_source"] == "classifier" for row in av_candidates)
    low_confidence_path = classification_output_dir / "low_confidence_jobs.jsonl"
    assert not any(line.strip() for line in low_confidence_path.read_text(encoding="utf-8").splitlines())
    assert not (classification_output_dir / "relevance_metrics.json").is_file()

    # Final enrichment output: the actual deliverable of the whole pipeline.
    av_jobs_path = classification_output_dir / "av_jobs.jsonl"
    assert av_jobs_path.is_file()
    av_jobs = {
        job["deduplication_key"]: job
        for job in (json.loads(line) for line in av_jobs_path.read_text(encoding="utf-8").splitlines())
    }
    assert set(av_jobs) == {"dk-perception-1", "dk-program-2"}

    keyword_resolved = av_jobs["dk-perception-1"]["_classification"]
    assert keyword_resolved["category_source"] == "keyword_resolved"
    assert keyword_resolved["categories"]

    llm_enriched = av_jobs["dk-program-2"]["_classification"]
    assert llm_enriched["category_source"] == "llm_enriched"
    assert llm_enriched["categories"] == ["System and Safety"]
    assert llm_enriched["skills"] == [{"name": "Program Management", "skill_type": "domain_concept"}]

    enrichment_metrics = json.loads(
        (classification_output_dir / "enrichment_metrics.json").read_text(encoding="utf-8")
    )
    assert enrichment_metrics["av_count"] == 2
    assert enrichment_metrics["failed_count"] == 0
    assert enrichment_metrics["keyword_resolved"] == 1
    assert enrichment_metrics["llm_enriched"] == 1


@patch("scrapers.utils.job_enricher.JobEnricher", _FakeEnricher)
@patch("scrapers.utils.job_enricher.GroqCompletion", lambda: None)
@patch("scrapers.utils.av_function_filter_cli.AVFunctionFilter", _FakeFunctionFilter)
@patch("scrapers.utils.av_function_filter_cli.GroqCompletion", lambda: None)
@patch("scrapers.utils.job_classifier.JobClassifier", _FakeRelevanceClassifier)
@patch("scrapers.utils.job_classifier.GroqCompletion", lambda: None)
@patch("scrapers.service.silver_cleaning.silver_export.psycopg2.connect")
@patch("scrapers.config.dbt.subprocess.run")
@patch("scrapers.response_archive.Minio")
@patch("scrapers.service.fetch.rawfetch.urlopen")
def test_pipeline_skip_flags_bypass_scrape_and_dbt_but_still_run_real_downstream_stages(
    mock_urlopen,
    mock_minio,
    mock_dbt_subprocess,
    mock_silver_connect,
    tmp_path,
):
    _stub_silver_export_rows(
        mock_silver_connect,
        [
            {
                "deduplication_key": "dk-perception-1",
                "company_name": "Stack AV",
                "job_name": "Object Detection Engineer",
                "job_description": "Build sensor fusion and lidar perception software for autonomous vehicles.",
            }
        ],
    )

    silver_export_path = tmp_path / "silver_export.jsonl"
    classification_output_dir = tmp_path / "job_classification"

    status = PipelineRunner.run(
        [
            "--skip-scrape",
            "--skip-silver-build",
            "--silver-export-path",
            str(silver_export_path),
            "--prefilter-output-dir",
            str(tmp_path / "job_prefilter"),
            "--classification-output-dir",
            str(classification_output_dir),
        ]
    )

    assert status == 0
    mock_urlopen.assert_not_called()
    mock_minio.assert_not_called()
    mock_dbt_subprocess.assert_not_called()

    # Silver export still ran for real against the mocked DB boundary, and
    # its output really fed the pre-filter/classify/enrich stages that follow.
    assert silver_export_path.is_file()
    av_jobs_path = classification_output_dir / "av_jobs.jsonl"
    assert av_jobs_path.is_file()
    av_jobs = [json.loads(line) for line in av_jobs_path.read_text(encoding="utf-8").splitlines()]
    assert len(av_jobs) == 1
    assert av_jobs[0]["deduplication_key"] == "dk-perception-1"
    assert av_jobs[0]["_classification"]["category_source"] == "keyword_resolved"
