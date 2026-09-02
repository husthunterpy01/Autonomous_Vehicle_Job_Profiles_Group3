from unittest.mock import MagicMock, patch

from scrapers.service.silver_cleaning.silver_ingest import SilverIngest


def _connection_with_rows(rows):
    connection = MagicMock()
    connection.__enter__.return_value = connection
    read_cursor = MagicMock()
    write_cursor = MagicMock()
    connection.cursor.side_effect = [
        MagicMock(
            __enter__=MagicMock(return_value=read_cursor),
            __exit__=MagicMock(return_value=False),
        ),
        MagicMock(
            __enter__=MagicMock(return_value=write_cursor),
            __exit__=MagicMock(return_value=False),
        ),
    ]
    read_cursor.fetchall.return_value = rows
    return connection, read_cursor, write_cursor


@patch("scrapers.service.silver_cleaning.silver_ingest.execute_values")
@patch("scrapers.service.silver_cleaning.silver_ingest.psycopg2.connect")
def test_ingest_reads_bronze_and_replaces_silver(mock_connect, mock_execute_values):
    connection, read_cursor, write_cursor = _connection_with_rows(
        [
            {
                "id": 12,
                "ats_name": "greenhouse",
                "company_name": "Stack AV",
                "job_name": " Perception Engineer ",
                "job_description": "<p>Build autonomy.</p>",
                "location": "Pittsburgh, PA | Remote",
                "job_url": "https://example.test/jobs/12",
                "job_uploaded_at": "2026-09-01T00:00:00Z",
                "employment_type": "Full Time",
            }
        ]
    )
    mock_connect.return_value = connection

    assert SilverIngest().run() == 0

    assert any(
        "SELECT * FROM bronze.job_postings" in call.args[0]
        for call in read_cursor.execute.call_args_list
    )
    assert any("TRUNCATE TABLE" in call.args[0] for call in write_cursor.execute.call_args_list)
    row = mock_execute_values.call_args.args[2][0]
    assert len(row[0]) == 64
    assert row[1] == "12"
    assert row[4:7] == ("Stack AV", "Perception Engineer", "Build autonomy.")
    assert row[8] == ["Pittsburgh, PA", "Remote"]
    connection.close.assert_called_once_with()


@patch("scrapers.service.silver_cleaning.silver_ingest.psycopg2.connect")
def test_ingest_returns_error_on_database_failure(mock_connect):
    mock_connect.side_effect = OSError("database unavailable")

    assert SilverIngest().run() == 1
