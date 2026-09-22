"""Coverage for the thin `python -m app.import_*` / `app.sync_silver` /
`app.validate_handoff` CLI wrappers - previously untested, so nothing ever
exercised their argv wiring or which SilverPipeline method each dispatches
to.
"""

import json
from unittest.mock import MagicMock, patch

import pytest


def _write_handoff(tmp_path, records):
    path = tmp_path / "handoff.json"
    path.write_text(json.dumps(records), encoding="utf-8")
    return path


@patch("app.import_categories.sync_if_configured")
@patch("app.import_categories.SilverPipeline")
def test_import_categories_reads_input_and_calls_silver_pipeline(
    mock_pipeline_cls, mock_sync, tmp_path, monkeypatch, capsys
):
    import app.import_categories as module

    path = _write_handoff(tmp_path, [{"functional_area": "Perception"}])
    monkeypatch.setattr("sys.argv", ["command", str(path)])
    mock_pipeline_cls.return_value.import_categories.return_value = {"imported": 1}

    module.main()

    mock_pipeline_cls.return_value.import_categories.assert_called_once_with([{"functional_area": "Perception"}])
    mock_sync.assert_called_once()
    assert json.loads(capsys.readouterr().out) == {"imported": 1}


@patch("app.import_salary.sync_if_configured")
@patch("app.import_salary.SilverPipeline")
def test_import_salary_reads_input_and_calls_silver_pipeline(
    mock_pipeline_cls, mock_sync, tmp_path, monkeypatch, capsys
):
    import app.import_salary as module

    path = _write_handoff(tmp_path, [{"salary_average": 150000}])
    monkeypatch.setattr("sys.argv", ["command", str(path)])
    mock_pipeline_cls.return_value.import_salary.return_value = {"imported": 1}

    module.main()

    mock_pipeline_cls.return_value.import_salary.assert_called_once_with([{"salary_average": 150000}])
    mock_sync.assert_called_once()
    assert json.loads(capsys.readouterr().out) == {"imported": 1}


@patch("app.import_skills.sync_if_configured")
@patch("app.import_skills.SilverPipeline")
def test_import_skills_reads_input_and_calls_silver_pipeline(
    mock_pipeline_cls, mock_sync, tmp_path, monkeypatch, capsys
):
    import app.import_skills as module

    path = _write_handoff(tmp_path, [{"skill": "ROS 2"}])
    monkeypatch.setattr("sys.argv", ["command", str(path)])
    mock_pipeline_cls.return_value.import_skills.return_value = {"imported": 1}

    module.main()

    mock_pipeline_cls.return_value.import_skills.assert_called_once_with([{"skill": "ROS 2"}])
    mock_sync.assert_called_once()
    assert json.loads(capsys.readouterr().out) == {"imported": 1}


@patch("app.validate_handoff.SilverPipeline")
def test_validate_handoff_reads_input_and_calls_silver_pipeline(mock_pipeline_cls, tmp_path, monkeypatch, capsys):
    import app.validate_handoff as module

    path = _write_handoff(tmp_path, [{"source_job_id": "abc"}])
    monkeypatch.setattr("sys.argv", ["command", str(path)])
    mock_pipeline_cls.return_value.validate.return_value = {"valid": 1}

    module.main()

    mock_pipeline_cls.return_value.validate.assert_called_once_with([{"source_job_id": "abc"}])
    assert json.loads(capsys.readouterr().out) == {"valid": 1}


def test_sync_silver_requires_allow_unclassified_flag(monkeypatch, capsys):
    import app.sync_silver as module

    monkeypatch.setattr("sys.argv", ["command"])

    with pytest.raises(SystemExit) as raised:
        module.main()

    assert raised.value.code == 2
    assert "not integrated yet" in capsys.readouterr().err


def test_sync_silver_requires_silver_database_url_env_var(monkeypatch, capsys):
    import app.sync_silver as module

    monkeypatch.setattr("sys.argv", ["command", "--allow-unclassified"])
    monkeypatch.delenv("SILVER_DATABASE_URL", raising=False)

    with pytest.raises(SystemExit) as raised:
        module.main()

    assert raised.value.code == 2
    assert "SILVER_DATABASE_URL" in capsys.readouterr().err


@patch("app.sync_silver.sync_if_configured")
@patch("app.sync_silver.SilverPipeline")
@patch("app.sync_silver.create_engine")
def test_sync_silver_syncs_and_disposes_the_source_engine(
    mock_create_engine, mock_pipeline_cls, mock_sync_if_configured, monkeypatch, capsys
):
    import app.sync_silver as module

    monkeypatch.setattr("sys.argv", ["command", "--allow-unclassified"])
    monkeypatch.setenv("SILVER_DATABASE_URL", "postgresql://source/db")
    mock_source_engine = MagicMock()
    mock_create_engine.return_value = mock_source_engine
    mock_pipeline_cls.return_value.sync.return_value = {"synced": 5}

    module.main()

    mock_create_engine.assert_called_once_with("postgresql://source/db", pool_pre_ping=True)
    mock_pipeline_cls.return_value.sync.assert_called_once_with(mock_source_engine, allow_unclassified=True)
    mock_source_engine.dispose.assert_called_once()
    mock_sync_if_configured.assert_called_once()
    assert json.loads(capsys.readouterr().out) == {"synced": 5}


@patch("app.sync_silver.SilverPipeline")
@patch("app.sync_silver.create_engine")
def test_sync_silver_disposes_the_source_engine_even_if_sync_raises(
    mock_create_engine, mock_pipeline_cls, monkeypatch
):
    import app.sync_silver as module

    monkeypatch.setattr("sys.argv", ["command", "--allow-unclassified"])
    monkeypatch.setenv("SILVER_DATABASE_URL", "postgresql://source/db")
    mock_source_engine = MagicMock()
    mock_create_engine.return_value = mock_source_engine
    mock_pipeline_cls.return_value.sync.side_effect = RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        module.main()

    mock_source_engine.dispose.assert_called_once()
