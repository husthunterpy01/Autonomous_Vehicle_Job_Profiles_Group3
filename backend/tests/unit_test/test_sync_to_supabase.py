import subprocess
from unittest.mock import MagicMock, patch

import pytest

from scripts.sync_to_supabase import (
    _grant_api_read_access,
    sync_if_configured,
    sync_to_supabase,
)


@patch("scripts.sync_to_supabase._grant_api_read_access")
def test_sync_to_supabase_dumps_then_restores(mock_grant, tmp_path, monkeypatch):
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        return subprocess.CompletedProcess(args, 0)

    monkeypatch.setattr("scripts.sync_to_supabase.subprocess.run", fake_run)

    sync_to_supabase("postgresql://local", "postgresql://supabase")

    assert calls[0][:2] == ["pg_dump", "postgresql://local"]
    assert "--schema" in calls[0] and "public" in calls[0]
    assert calls[1][:3] == ["pg_restore", "-d", "postgresql://supabase"]
    assert "--clean" in calls[1] and "--if-exists" in calls[1]
    # both invocations reference the same dump file path
    dump_path_dump = calls[0][calls[0].index("-f") + 1]
    dump_path_restore = calls[1][-1]
    assert dump_path_dump == dump_path_restore
    mock_grant.assert_called_once_with("postgresql://supabase")


@patch("scripts.sync_to_supabase._grant_api_read_access")
def test_sync_to_supabase_survives_grant_failure(mock_grant, monkeypatch):
    # A GRANT hiccup (e.g. roles missing on a non-Supabase target) must not
    # fail the whole sync - the data mirror itself already succeeded.
    mock_grant.side_effect = RuntimeError("connection refused")
    monkeypatch.setattr(
        "scripts.sync_to_supabase.subprocess.run",
        lambda args, **kwargs: subprocess.CompletedProcess(args, 0),
    )

    sync_to_supabase("postgresql://local", "postgresql://supabase")  # does not raise


def test_grant_api_read_access_runs_expected_statements():
    executed = []
    mock_cursor = MagicMock()
    mock_cursor.execute.side_effect = lambda sql: executed.append(sql)
    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    with patch("psycopg2.connect", return_value=mock_conn) as mock_connect:
        _grant_api_read_access("postgresql://supabase")

    mock_connect.assert_called_once_with("postgresql://supabase")
    assert mock_conn.autocommit is True
    assert any("GRANT USAGE ON SCHEMA public TO anon, authenticated" in s for s in executed)
    assert any("GRANT SELECT ON ALL TABLES IN SCHEMA public TO anon, authenticated" in s for s in executed)
    assert any("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO anon, authenticated" in s for s in executed)
    mock_conn.close.assert_called_once()


def test_sync_if_configured_skips_when_target_unset(monkeypatch, caplog):
    monkeypatch.delenv("SUPABASE_DATABASE_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://local")

    with caplog.at_level("INFO"):
        result = sync_if_configured()

    assert result is False
    assert any("skipping" in m.lower() for m in caplog.messages)


def test_sync_if_configured_warns_when_source_unset(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("SUPABASE_DATABASE_URL", "postgresql://supabase")

    assert sync_if_configured() is False


@patch("scripts.sync_to_supabase.sync_to_supabase")
def test_sync_if_configured_calls_sync_when_both_set(mock_sync, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://local")
    monkeypatch.setenv("SUPABASE_DATABASE_URL", "postgresql://supabase")

    result = sync_if_configured()

    assert result is True
    mock_sync.assert_called_once_with("postgresql://local", "postgresql://supabase")


@patch("scripts.sync_to_supabase.sync_to_supabase")
def test_sync_if_configured_swallows_failure_by_default(mock_sync, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://local")
    monkeypatch.setenv("SUPABASE_DATABASE_URL", "postgresql://supabase")
    mock_sync.side_effect = subprocess.CalledProcessError(1, ["pg_restore"], stderr="boom")

    assert sync_if_configured() is False  # does not raise


@patch("scripts.sync_to_supabase.sync_to_supabase")
def test_sync_if_configured_raises_when_required(mock_sync, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://local")
    monkeypatch.setenv("SUPABASE_DATABASE_URL", "postgresql://supabase")
    mock_sync.side_effect = subprocess.CalledProcessError(1, ["pg_restore"], stderr="boom")

    with pytest.raises(RuntimeError, match="boom"):
        sync_if_configured(required=True)
