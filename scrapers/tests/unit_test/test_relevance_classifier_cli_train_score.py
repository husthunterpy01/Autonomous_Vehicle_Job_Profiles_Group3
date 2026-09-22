"""Coverage for relevance_classifier_cli.py's train/score commands.

Unlike test_relevance_classifier_cli.py, this file exercises the real CLI
entrypoints. train/score default to the embedding backend.
"""

import json

import pytest
from scrapers.utils.relevance_classifier_cli import main

AV_RECORDS = [
    {
        "deduplication_key": "av-1",
        "title": "Perception Engineer",
        "description": "Build lidar sensor fusion perception software for autonomous vehicles.",
    },
    {
        "deduplication_key": "av-2",
        "title": "Autonomy Software Engineer",
        "description": "Develop autonomous vehicle perception and sensor fusion pipelines using lidar data.",
    },
    {
        "deduplication_key": "av-3",
        "title": "Sensor Fusion Engineer",
        "description": "Design lidar radar sensor fusion algorithms for the autonomous vehicle perception stack.",
    },
    {
        "deduplication_key": "av-4",
        "title": "Localization Engineer",
        "description": "Implement autonomous vehicle localization using lidar point cloud perception data.",
    },
    {
        "deduplication_key": "av-5",
        "title": "Planning Engineer",
        "description": "Build motion planning software for the autonomous vehicle perception and sensor fusion stack.",
    },
    {
        "deduplication_key": "av-6",
        "title": "Robotics Perception Engineer",
        "description": "Work on lidar camera sensor fusion perception for autonomous robotics vehicles.",
    },
]

NON_AV_RECORDS = [
    {
        "deduplication_key": "hr-1",
        "title": "Payroll Specialist",
        "description": "Process employee payroll, benefits, and compensation for human resources.",
    },
    {
        "deduplication_key": "hr-2",
        "title": "HR Coordinator",
        "description": "Support human resources payroll benefits administration and employee compensation.",
    },
    {
        "deduplication_key": "hr-3",
        "title": "Accounts Payable Clerk",
        "description": "Handle accounts payable invoices, payroll compensation, and vendor payments.",
    },
    {
        "deduplication_key": "hr-4",
        "title": "Benefits Administrator",
        "description": "Manage employee benefits, payroll compensation, and human resources programs.",
    },
    {
        "deduplication_key": "hr-5",
        "title": "Recruiting Coordinator",
        "description": "Coordinate recruiting, human resources, payroll, and employee compensation tasks.",
    },
    {
        "deduplication_key": "hr-6",
        "title": "Office Administrator",
        "description": "Administer payroll, benefits, human resources, compensation, and office operations.",
    },
]


def _write_jsonl(path, records):
    with path.open("w", encoding="utf-8") as stream:
        for record in records:
            stream.write(json.dumps(record) + "\n")


def _write_seed_dir(output_dir, av_records=AV_RECORDS, non_av_records=NON_AV_RECORDS):
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_jsonl(output_dir / "av_candidates.jsonl", av_records)
    _write_jsonl(output_dir / "non_av_jobs.jsonl", non_av_records)


def test_train_saves_a_model_and_reports_example_counts(tmp_path, capsys):
    output_dir = tmp_path / "job_classification"
    _write_seed_dir(output_dir)
    model_path = tmp_path / "model.joblib"

    status = main(
        [
            "train",
            "--output-dir", str(output_dir),
            "--model", str(model_path),
            "--test-size", "0",
        ]
    )

    assert status == 0
    assert model_path.is_file()
    result = json.loads(capsys.readouterr().out)
    assert result["av_examples"] == len(AV_RECORDS)
    assert result["non_av_examples"] == len(NON_AV_RECORDS)
    assert result["model"] == str(model_path)
    assert "evaluation" not in result


def test_train_raises_systemexit_without_both_classes(tmp_path):
    output_dir = tmp_path / "job_classification"
    _write_seed_dir(output_dir, non_av_records=[])

    with pytest.raises(SystemExit):
        main(["train", "--output-dir", str(output_dir), "--test-size", "0"])


def test_train_only_llm_labeled_excludes_classifier_predictions(tmp_path, capsys):
    output_dir = tmp_path / "job_classification"
    classifier_labeled = {
        "deduplication_key": "av-classifier-1",
        "title": "Perception Engineer",
        "description": "Build lidar sensor fusion perception software for autonomous vehicles.",
        "_classification": {"_source": "classifier"},
    }
    _write_seed_dir(output_dir, av_records=[*AV_RECORDS, classifier_labeled])

    status = main(["train", "--output-dir", str(output_dir), "--test-size", "0", "--only-llm-labeled"])

    assert status == 0
    result = json.loads(capsys.readouterr().out)
    # The classifier-labeled extra record must be excluded, not counted.
    assert result["av_examples"] == len(AV_RECORDS)


def test_train_with_held_out_split_reports_evaluation_metrics(tmp_path, capsys):
    output_dir = tmp_path / "job_classification"
    _write_seed_dir(output_dir)
    model_path = tmp_path / "model.joblib"

    status = main(
        [
            "train",
            "--output-dir", str(output_dir),
            "--model", str(model_path),
            "--test-size", "0.4",
            "--split-seed", "1",
        ]
    )

    assert status == 0
    result = json.loads(capsys.readouterr().out)
    evaluation = result["evaluation"]
    assert set(evaluation) == {"train", "held_out", "overfit_gap_accuracy"}
    assert set(evaluation["held_out"]) == {
        "examples", "accuracy", "precision", "recall", "f1", "confusion_matrix",
    }


def test_score_writes_classification_outputs_for_pending_jobs(tmp_path):
    seed_dir = tmp_path / "job_classification"
    _write_seed_dir(seed_dir)
    model_path = tmp_path / "model.joblib"
    assert main(["train", "--output-dir", str(seed_dir), "--model", str(model_path), "--test-size", "0"]) == 0

    input_path = tmp_path / "unlabeled.jsonl"
    pending = [
        {
            "deduplication_key": "pending-1",
            "title": "Perception Software Engineer",
            "description": "Build lidar sensor fusion perception software for autonomous vehicles.",
        },
        {
            "deduplication_key": "pending-2",
            "title": "Payroll Analyst",
            "description": "Process employee payroll, benefits, and compensation for human resources.",
        },
    ]
    _write_jsonl(input_path, pending)

    score_output_dir = tmp_path / "scored"
    status = main(
        [
            "score",
            "--input", str(input_path),
            "--output-dir", str(score_output_dir),
            "--model", str(model_path),
        ]
    )

    assert status == 0
    av_lines = (score_output_dir / "av_candidates.jsonl").read_text(encoding="utf-8").splitlines()
    non_av_lines = (score_output_dir / "non_av_jobs.jsonl").read_text(encoding="utf-8").splitlines()
    low_confidence_lines = (score_output_dir / "low_confidence_jobs.jsonl").read_text(encoding="utf-8").splitlines()
    scored_ids = set()
    for line in [*av_lines, *non_av_lines, *low_confidence_lines]:
        record = json.loads(line)
        scored_ids.add(record["_job_id"])
        classification = record["_classification"]
        assert classification["_source"] == "classifier"
        assert "is_av_relevant" in classification
        assert classification["confidence"] in {"High", "Medium", "Low"}
    assert scored_ids == {"pending-1", "pending-2"}


def test_score_skips_already_processed_job_ids(tmp_path):
    seed_dir = tmp_path / "job_classification"
    _write_seed_dir(seed_dir)
    model_path = tmp_path / "model.joblib"
    assert main(["train", "--output-dir", str(seed_dir), "--model", str(model_path), "--test-size", "0"]) == 0

    input_path = tmp_path / "unlabeled.jsonl"
    _write_jsonl(
        input_path,
        [
            {
                "deduplication_key": "pending-1",
                "title": "Perception Software Engineer",
                "description": "Build lidar sensor fusion perception software for autonomous vehicles.",
            }
        ],
    )

    score_output_dir = tmp_path / "scored"
    score_output_dir.mkdir()
    (score_output_dir / "av_candidates.jsonl").write_text(
        json.dumps({"deduplication_key": "pending-1", "_job_id": "pending-1"}) + "\n", encoding="utf-8"
    )

    status = main(
        [
            "score",
            "--input", str(input_path),
            "--output-dir", str(score_output_dir),
            "--model", str(model_path),
        ]
    )

    assert status == 0
    # Nothing new should have been appended - the one pending job was already
    # in av_candidates.jsonl from a prior run.
    av_lines = (score_output_dir / "av_candidates.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(av_lines) == 1
    assert not (score_output_dir / "non_av_jobs.jsonl").is_file()
    assert not (score_output_dir / "low_confidence_jobs.jsonl").is_file()


def test_score_with_no_pending_jobs_reports_zero_counts(tmp_path, capsys):
    seed_dir = tmp_path / "job_classification"
    _write_seed_dir(seed_dir)
    model_path = tmp_path / "model.joblib"
    assert main(["train", "--output-dir", str(seed_dir), "--model", str(model_path), "--test-size", "0"]) == 0
    capsys.readouterr()  # discard train()'s own printed output

    input_path = tmp_path / "empty.jsonl"
    _write_jsonl(input_path, [])

    status = main(
        [
            "score",
            "--input", str(input_path),
            "--output-dir", str(tmp_path / "scored"),
            "--model", str(model_path),
        ]
    )

    assert status == 0
    result = json.loads(capsys.readouterr().out)
    assert result == {"scored": 0, "confident_av": 0, "confident_non_av": 0, "low_confidence": 0}
