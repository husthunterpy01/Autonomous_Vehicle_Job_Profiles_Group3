import subprocess
from unittest.mock import MagicMock, patch

from scrapers.service.silver_cleaning.gold_sync import (
    main,
    sync_gold,
    sync_gold_if_configured,
)


@patch("scrapers.service.silver_cleaning.gold_sync.subprocess.run")
def test_sync_dumps_the_gold_schema_and_replaces_it_in_one_transaction(mock_run):
    sync_gold("host=warehouse", "postgresql://gold-db")

    dump, restore = (call.args[0] for call in mock_run.call_args_list)
    assert dump[:5] == ["pg_dump", "-d", "host=warehouse", "--schema", "gold"]
    assert restore[:3] == ["pg_restore", "-d", "postgresql://gold-db"]
    assert {"--clean", "--if-exists", "--single-transaction"} <= set(restore)
    assert dump[-1] == restore[-1]


@patch("scrapers.service.silver_cleaning.gold_sync.sync_gold")
def test_sync_is_skipped_when_no_gold_database_is_configured(mock_sync, monkeypatch):
    monkeypatch.delenv("GOLD_DATABASE_URL", raising=False)
    assert sync_gold_if_configured(MagicMock()) == 0
    mock_sync.assert_not_called()


@patch("scrapers.service.silver_cleaning.gold_sync.sync_gold")
def test_sync_copies_from_the_warehouse_to_the_gold_database(mock_sync, monkeypatch):
    monkeypatch.setenv("GOLD_DATABASE_URL", "postgresql://gold-db")
    config = MagicMock()
    config.dsn.return_value = "host=warehouse"
    assert sync_gold_if_configured(config) == 0
    mock_sync.assert_called_once_with("host=warehouse", "postgresql://gold-db")


@patch("scrapers.service.silver_cleaning.gold_sync.sync_gold")
def test_a_failed_copy_or_missing_binary_returns_1(mock_sync, monkeypatch):
    monkeypatch.setenv("GOLD_DATABASE_URL", "postgresql://gold-db")
    mock_sync.side_effect = subprocess.CalledProcessError(1, ["pg_restore"], stderr="connection refused")
    assert sync_gold_if_configured(MagicMock()) == 1
    mock_sync.side_effect = FileNotFoundError("pg_dump")
    assert sync_gold_if_configured(MagicMock()) == 1


def test_standalone_command_requires_a_gold_database(monkeypatch):
    monkeypatch.delenv("GOLD_DATABASE_URL", raising=False)
    assert main() == 1
