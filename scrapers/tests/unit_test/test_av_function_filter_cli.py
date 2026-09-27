import json
from unittest.mock import patch

from scrapers.utils.av_function_filter_cli import AVFunctionFilterMain


class _FakeFunctionFilter:
    """Answers directly from the job ids/titles it actually received, instead
    of mocking GroqCompletion and round-tripping through real prompt-building
    + JSON response parsing. Mirrors test_job_classifier_cli.py's
    _FakeRelevanceClassifier pattern. Only titles containing "Manager" are
    treated as confirmed non-engineering, so the fixture can drive both
    outcomes from one instance."""

    def __init__(self, *_args, **_kwargs):
        pass

    def classify_batch(self, jobs):
        from scrapers.service.llm import FunctionDecision

        results = {}
        for job in jobs:
            is_engineering = "Manager" not in job["title"]
            results[job["id"]] = FunctionDecision(is_engineering, "High", "fixture")
        return results


@patch("scrapers.utils.av_function_filter_cli.AVFunctionFilter", _FakeFunctionFilter)
@patch("scrapers.utils.av_function_filter_cli.GroqCompletion", lambda: None)
def test_unflagged_titles_pass_through_without_an_llm_call(tmp_path):
    input_path = tmp_path / "av_candidates.jsonl"
    with input_path.open("w", encoding="utf-8") as stream:
        stream.write(json.dumps({"deduplication_key": "eng-1", "job_name": "Perception Engineer"}) + "\n")

    output_dir = tmp_path / "job_classification"
    status = AVFunctionFilterMain.main(["--input", str(input_path), "--output-dir", str(output_dir)])

    assert status == 0
    engineering_lines = (output_dir / "av_engineering_candidates.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(engineering_lines) == 1
    record = json.loads(engineering_lines[0])
    assert record["_job_id"] == "eng-1"
    assert "_function_filter" not in record

    metrics = json.loads((output_dir / "function_filter_metrics.json").read_text(encoding="utf-8"))
    assert metrics["passed_through_count"] == 1
    assert metrics["llm_confirmed_engineering_count"] == 0
    assert metrics["non_engineering_count"] == 0


@patch("scrapers.utils.av_function_filter_cli.AVFunctionFilter", _FakeFunctionFilter)
@patch("scrapers.utils.av_function_filter_cli.GroqCompletion", lambda: None)
def test_flagged_title_splits_between_engineering_and_non_engineering(tmp_path):
    input_path = tmp_path / "av_candidates.jsonl"
    with input_path.open("w", encoding="utf-8") as stream:
        stream.write(
            json.dumps({"deduplication_key": "pm-1", "job_name": "Senior Technical Program Manager"}) + "\n"
        )
        stream.write(
            json.dumps(
                {"deduplication_key": "eng-2", "job_name": "Senior Staff Regulatory and Compliance Engineer"}
            )
            + "\n"
        )

    output_dir = tmp_path / "job_classification"
    status = AVFunctionFilterMain.main(["--input", str(input_path), "--output-dir", str(output_dir)])

    assert status == 0
    non_engineering = (output_dir / "non_engineering_jobs.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(non_engineering) == 1
    assert json.loads(non_engineering[0])["_job_id"] == "pm-1"

    engineering_lines = (output_dir / "av_engineering_candidates.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(engineering_lines) == 1
    assert json.loads(engineering_lines[0])["_job_id"] == "eng-2"

    metrics = json.loads((output_dir / "function_filter_metrics.json").read_text(encoding="utf-8"))
    # "Regulatory and Compliance Engineer" doesn't match the non-engineering
    # title pattern at all, so it passes through with no LLM call - only the
    # "Technical Program Manager" title is flagged and sent to the (fake) LLM.
    assert metrics["passed_through_count"] == 1
    assert metrics["non_engineering_count"] == 1
    assert metrics["llm_confirmed_engineering_count"] == 0


@patch("scrapers.utils.av_function_filter_cli.AVFunctionFilter", _FakeFunctionFilter)
@patch("scrapers.utils.av_function_filter_cli.GroqCompletion", lambda: None)
def test_main_resumes_and_skips_already_processed_job_ids(tmp_path):
    input_path = tmp_path / "av_candidates.jsonl"
    with input_path.open("w", encoding="utf-8") as stream:
        stream.write(json.dumps({"deduplication_key": "existing-1", "job_name": "Old Role"}) + "\n")
        stream.write(json.dumps({"deduplication_key": "new-2", "job_name": "New Role"}) + "\n")

    output_dir = tmp_path / "job_classification"
    output_dir.mkdir()
    (output_dir / "av_engineering_candidates.jsonl").write_text(
        json.dumps({"deduplication_key": "existing-1", "_job_id": "existing-1"}) + "\n", encoding="utf-8"
    )

    status = AVFunctionFilterMain.main(["--input", str(input_path), "--output-dir", str(output_dir)])

    assert status == 0
    engineering_lines = (output_dir / "av_engineering_candidates.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(engineering_lines) == 2
    job_ids = {json.loads(line)["_job_id"] for line in engineering_lines}
    assert job_ids == {"existing-1", "new-2"}

    metrics = json.loads((output_dir / "function_filter_metrics.json").read_text(encoding="utf-8"))
    assert metrics["skipped_already_processed"] == 1
