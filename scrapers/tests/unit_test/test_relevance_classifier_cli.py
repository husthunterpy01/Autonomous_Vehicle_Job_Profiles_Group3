import pytest

pytest.importorskip("setfit")

from unittest.mock import patch

from scrapers.utils.relevance_classifier_cli import _build_parser, _load_classifier


@patch("scrapers.service.ml.setfit_classifier.SetFitRelevanceClassifier.load")
def test_load_classifier_defaults_to_published_hf_repo_for_setfit(mock_load, tmp_path):
    _load_classifier("setfit", tmp_path / "missing")
    mock_load.assert_called_once_with(tmp_path / "missing")


@patch("scrapers.service.ml.setfit_classifier.SetFitRelevanceClassifier.load")
def test_load_classifier_disables_fallback_when_hf_repo_id_is_empty_string(mock_load, tmp_path):
    _load_classifier("setfit", tmp_path / "missing", hf_repo_id="")
    mock_load.assert_called_once_with(tmp_path / "missing", hf_repo_id=None)


@patch("scrapers.service.ml.setfit_classifier.SetFitRelevanceClassifier.load")
def test_load_classifier_passes_through_a_custom_hf_repo_id(mock_load, tmp_path):
    _load_classifier("setfit", tmp_path / "missing", hf_repo_id="someone/other-repo")
    mock_load.assert_called_once_with(tmp_path / "missing", hf_repo_id="someone/other-repo")


def test_score_subcommand_accepts_hf_repo_id_flag():
    args = _build_parser().parse_args(["score", "--input", "x.jsonl", "--backend", "setfit", "--hf-repo-id", "a/b"])
    assert args.hf_repo_id == "a/b"


def test_score_subcommand_hf_repo_id_defaults_to_none():
    args = _build_parser().parse_args(["score", "--input", "x.jsonl"])
    assert args.hf_repo_id is None
