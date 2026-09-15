from unittest.mock import MagicMock, patch

from scrapers.service.silver_cleaning.silver_export import SilverExport, main


@patch("scrapers.service.silver_cleaning.silver_export.psycopg2.connect")
def test_export_writes_silver_rows_to_jsonl(mock_connect, tmp_path):
    connection = mock_connect.return_value
    cursor = MagicMock()
    cursor.__iter__.return_value = iter(
        [
            {"deduplication_key": "a", "company_name": "Stack AV", "job_name": "Engineer"},
            {"deduplication_key": "b", "company_name": "Waabi", "job_name": "Scientist"},
        ]
    )
    connection.cursor.return_value.__enter__.return_value = cursor

    output_path = tmp_path / "silver_export.jsonl"
    count = SilverExport().export(output_path)

    assert count == 2
    lines = output_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert "Stack AV" in lines[0]
    connection.close.assert_called_once()


@patch("scrapers.service.silver_cleaning.silver_export.psycopg2.connect")
def test_export_creates_parent_directory(mock_connect, tmp_path):
    connection = mock_connect.return_value
    cursor = MagicMock()
    cursor.__iter__.return_value = iter([])
    connection.cursor.return_value.__enter__.return_value = cursor

    output_path = tmp_path / "nested" / "silver_export.jsonl"
    count = SilverExport().export(output_path)

    assert count == 0
    assert output_path.is_file()


@patch("scrapers.service.silver_cleaning.silver_export.psycopg2.connect")
def test_main_writes_to_the_requested_output_path(mock_connect, tmp_path):
    connection = mock_connect.return_value
    cursor = MagicMock()
    cursor.__iter__.return_value = iter([{"deduplication_key": "a"}])
    connection.cursor.return_value.__enter__.return_value = cursor

    output_path = tmp_path / "custom_export.jsonl"
    status = main(["--output", str(output_path)])

    assert status == 0
    assert output_path.is_file()
