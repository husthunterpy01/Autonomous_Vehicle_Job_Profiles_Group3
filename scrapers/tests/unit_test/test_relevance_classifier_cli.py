import json
from unittest.mock import patch

import pytest
from scrapers.utils.relevance_classifier_cli import (
    _build_parser,
    _load_classifier,
    score,
)


@patch("scrapers.service.ml.setfit_classifier.SetFitRelevanceClassifier.load")
def test_load_classifier_defaults_to_published_hf_repo_for_setfit(mock_load, tmp_path):
    pytest.importorskip("setfit")
    _load_classifier("setfit", tmp_path / "missing")
    mock_load.assert_called_once_with(tmp_path / "missing")


@patch("scrapers.service.ml.setfit_classifier.SetFitRelevanceClassifier.load")
def test_load_classifier_disables_fallback_when_hf_repo_id_is_empty_string(mock_load, tmp_path):
    pytest.importorskip("setfit")
    _load_classifier("setfit", tmp_path / "missing", hf_repo_id="")
    mock_load.assert_called_once_with(tmp_path / "missing", hf_repo_id=None)


@patch("scrapers.service.ml.setfit_classifier.SetFitRelevanceClassifier.load")
def test_load_classifier_passes_through_a_custom_hf_repo_id(mock_load, tmp_path):
    pytest.importorskip("setfit")
    _load_classifier("setfit", tmp_path / "missing", hf_repo_id="someone/other-repo")
    mock_load.assert_called_once_with(tmp_path / "missing", hf_repo_id="someone/other-repo")


@patch("scrapers.service.ml.embedding_classifier.EmbeddingRelevanceClassifier.load")
def test_load_classifier_defaults_to_published_hf_repo_for_embedding(mock_load, tmp_path):
    _load_classifier("embedding", tmp_path / "missing")
    mock_load.assert_called_once_with(tmp_path / "missing")


@patch("scrapers.service.ml.embedding_classifier.EmbeddingRelevanceClassifier.load")
def test_load_classifier_passes_hf_repo_id_for_embedding(mock_load, tmp_path):
    _load_classifier("embedding", tmp_path / "missing", hf_repo_id="someone/embedding")
    mock_load.assert_called_once_with(tmp_path / "missing", hf_repo_id="someone/embedding")


@patch("scrapers.service.ml.embedding_classifier.EmbeddingRelevanceClassifier.load")
def test_load_classifier_disables_embedding_fallback_when_hf_repo_id_is_empty(mock_load, tmp_path):
    _load_classifier("embedding", tmp_path / "missing", hf_repo_id="")
    mock_load.assert_called_once_with(tmp_path / "missing", hf_repo_id=None)


def test_score_subcommand_accepts_hf_repo_id_flag():
    args = _build_parser().parse_args(["score", "--input", "x.jsonl", "--backend", "setfit", "--hf-repo-id", "a/b"])
    assert args.hf_repo_id == "a/b"


def test_score_and_train_default_to_embedding_backend():
    score_args = _build_parser().parse_args(["score", "--input", "x.jsonl"])
    train_args = _build_parser().parse_args(["train"])
    assert score_args.backend == "embedding"
    assert train_args.backend == "embedding"
    assert score_args.hf_repo_id is None


def test_score_keys_jobs_by_deduplication_key(tmp_path, capsys):
    input_path = tmp_path / "pending.jsonl"
    rows = [
        {
            "deduplication_key": "hash-a",
            "source_job_id": "1",
            "company_name": "Acme",
            "job_title": "Perception Engineer",
            "job_description": "LiDAR fusion for autonomous driving.",
        },
        {
            "deduplication_key": "hash-b",
            "source_job_id": "1",
            "company_name": "OtherCo",
            "job_title": "Accountant",
            "job_description": "Month-end close and accounts payable.",
        },
    ]
    input_path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    output_dir = tmp_path / "out"

    class _FakeClassifier:
        def predict_proba(self, texts):
            assert len(texts) == 2
            return [0.9, 0.1]

    args = _build_parser().parse_args(
        ["score", "--input", str(input_path), "--output-dir", str(output_dir), "--backend", "tfidf"]
    )
    with patch(
        "scrapers.utils.relevance_classifier_cli._load_classifier",
        return_value=_FakeClassifier(),
    ):
        assert score(args) == 0

    av_ids = {
        json.loads(line)["_job_id"]
        for line in (output_dir / "av_candidates.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    non_av_ids = {
        json.loads(line)["_job_id"]
        for line in (output_dir / "non_av_jobs.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    assert av_ids == {"hash-a"}
    assert non_av_ids == {"hash-b"}
    capsys.readouterr()
