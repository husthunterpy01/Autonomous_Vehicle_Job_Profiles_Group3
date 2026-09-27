import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from scrapers.service.silver_cleaning.classification_ingest import (
    ClassificationIngest,
    ClassifiedJob,
    main,
    parse_run,
    parse_scraped_at,
    read_jsonl,
)

KEY_A = "a" * 32
KEY_B = "b" * 32
MAIN_TYPES = {"Perception": "Perception & Sensing", "Sensing": "Perception & Sensing", "Planning": "Decision"}
SCRAPED_AT = datetime(2026, 8, 31, 12, tzinfo=timezone.utc)


def job(key=KEY_A, title="Perception Engineer", skills=None, categories=None, relevant="True"):
    return {
        "deduplication_key": key,
        "job_name": title,
        "_classification": {
            "is_av_relevant": relevant,
            "categories": categories if categories is not None else [],
            "skills": skills if skills is not None else [{"name": "LiDAR", "skill_type": "domain_concept"}],
        },
    }


def test_parse_normalizes_title_and_skills_and_resolves_main_type():
    jobs, skipped = parse_run(
        [job(title="  Perception   Engineer ", categories=["Perception", "Sensing"], skills=[
            {"name": "Machine  Learning", "skill_type": "domain_concept"},
            {"name": "machine learning", "skill_type": "domain_concept"},
            {"name": "PyTorch", "skill_type": "framework"},
        ])],
        MAIN_TYPES,
    )
    assert skipped == 0
    assert jobs == [ClassifiedJob(
        deduplication_key=KEY_A,
        title="Perception Engineer",
        main_type="Perception & Sensing",
        skills=(("machine learning", "domain_concept", "Machine  Learning"), ("pytorch", "framework", "PyTorch")),
    )]


def test_no_or_unknown_categories_give_no_main_type_and_no_skills_is_kept():
    jobs, _ = parse_run([job(KEY_A, categories=[], skills=[]), job(KEY_B, categories=["Unknown"])], MAIN_TYPES)
    assert [(j.main_type, j.skills) for j in jobs] == [(None, ()), (None, (("lidar", "domain_concept", "LiDAR"),))]


@pytest.mark.parametrize("relevant", ["False", "false", False])
def test_rows_marked_not_av_are_skipped(relevant):
    assert parse_run([job(relevant=relevant)], MAIN_TYPES) == ([], 1)


@pytest.mark.parametrize(
    ("row", "message"),
    [
        ({**job(), "deduplication_key": "not-md5"}, "deduplication_key"),
        ({**job(), "job_name": " "}, "job_name"),
        ({"deduplication_key": KEY_A, "job_name": "x"}, "_classification"),
        (job(skills=[{"name": "LiDAR", "skill_type": "hardware"}]), "Invalid skill"),
        (job(categories="Perception"), "categories"),
    ],
)
def test_malformed_rows_reject_the_run(row, message):
    with pytest.raises(ValueError, match=message):
        parse_run([row], MAIN_TYPES)


def test_duplicate_jobs_in_a_run_are_rejected():
    with pytest.raises(ValueError, match="Row 2: Duplicate deduplication_key"):
        parse_run([job(), job()], MAIN_TYPES)


def test_scraped_at_needs_a_timezone():
    assert parse_scraped_at("2026-08-31T12:00:00Z") == SCRAPED_AT
    assert parse_scraped_at("2026-09-01T02:00:00+08:00").utcoffset() == timedelta(hours=8)
    with pytest.raises(ValueError, match="timezone"):
        parse_scraped_at("2026-08-31T12:00:00")


def test_read_jsonl_skips_blank_lines_and_reports_bad_ones(tmp_path):
    path = tmp_path / "av_jobs.jsonl"
    path.write_text(json.dumps(job()) + "\n\n" + json.dumps(job(KEY_B)) + "\n", encoding="utf-8")
    assert len(read_jsonl(path)) == 2
    path.write_text(json.dumps(job()) + "\n{broken\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Line 2"):
        read_jsonl(path)


def _connect_mock(rowcount=1):
    connection = MagicMock()
    cursor = connection.cursor.return_value.__enter__.return_value
    cursor.rowcount = rowcount
    return connection, cursor


@patch("scrapers.service.silver_cleaning.classification_ingest.execute_values")
@patch("scrapers.service.silver_cleaning.classification_ingest.psycopg2.connect")
def test_ingest_writes_the_run_its_jobs_and_skills(mock_connect, mock_execute_values):
    connection, cursor = _connect_mock()
    mock_connect.return_value = connection
    jobs, _ = parse_run([job(KEY_A, categories=["Planning"]), job(KEY_B, skills=[])], MAIN_TYPES)

    result = ClassificationIngest(MagicMock(), MagicMock()).ingest(jobs, scraped_at=SCRAPED_AT, source="backfill")

    assert result == {"status": "ingested", "scraped_at": SCRAPED_AT.isoformat(), "jobs": 2,
                      "jobs_without_skills": 1, "skill_rows": 1}
    run_insert = cursor.execute.call_args_list[1]
    assert run_insert.args[1] == (SCRAPED_AT, "backfill", None, True, 2)
    job_rows, skill_rows = (call.args[2] for call in mock_execute_values.call_args_list)
    assert job_rows == [(SCRAPED_AT, KEY_A, "Perception Engineer", "Decision"), (SCRAPED_AT, KEY_B, "Perception Engineer", None)]
    assert skill_rows == [(SCRAPED_AT, KEY_A, "lidar", "domain_concept", "LiDAR")]
    connection.close.assert_called_once()


@patch("scrapers.service.silver_cleaning.classification_ingest.execute_values")
@patch("scrapers.service.silver_cleaning.classification_ingest.psycopg2.connect")
def test_an_ingested_run_is_a_no_op_unless_replaced(mock_connect, mock_execute_values):
    connection, cursor = _connect_mock(rowcount=0)
    mock_connect.return_value = connection
    ingest = ClassificationIngest(MagicMock(), MagicMock())

    assert ingest.ingest([], scraped_at=SCRAPED_AT)["status"] == "already_ingested"
    mock_execute_values.assert_not_called()

    cursor.rowcount = 1
    assert ingest.ingest([], scraped_at=SCRAPED_AT, replace=True)["status"] == "replaced"
    assert "DELETE FROM silver.classification_run" in cursor.execute.call_args_list[-2].args[0]


@patch("scrapers.service.silver_cleaning.classification_ingest.execute_values")
@patch("scrapers.service.silver_cleaning.classification_ingest.psycopg2.connect")
def test_an_incomplete_run_is_registered_without_jobs(mock_connect, mock_execute_values):
    connection, cursor = _connect_mock()
    mock_connect.return_value = connection

    result = ClassificationIngest(MagicMock(), MagicMock()).ingest([], scraped_at=SCRAPED_AT, completed=False)

    assert result["status"] == "registered_incomplete"
    assert cursor.execute.call_args_list[1].args[1][3] is False
    mock_execute_values.assert_not_called()


def test_ingest_rejects_a_naive_timestamp_or_unknown_source():
    ingest = ClassificationIngest(MagicMock(), MagicMock())
    with pytest.raises(ValueError, match="timezone"):
        ingest.ingest([], scraped_at=SCRAPED_AT.replace(tzinfo=None))
    with pytest.raises(ValueError, match="source"):
        ingest.ingest([], scraped_at=SCRAPED_AT, source="manual")


def test_build_gold_runs_the_gold_dbt_models():
    postgres_config, dbt_config = MagicMock(), MagicMock()
    dbt_config.run.return_value = 0
    assert ClassificationIngest(postgres_config, dbt_config).build_gold() == 0
    dbt_config.run.assert_called_once_with("tag:gold", postgres_config)


@patch("scrapers.service.silver_cleaning.classification_ingest.sync_gold_if_configured", return_value=0)
@patch("scrapers.service.silver_cleaning.classification_ingest.ClassificationIngest")
def test_main_ingests_then_builds_and_syncs_gold(mock_ingest, mock_sync, tmp_path):
    path = tmp_path / "av_jobs.jsonl"
    path.write_text(json.dumps(job()) + "\n", encoding="utf-8")
    mock_ingest.return_value.ingest.return_value = {"status": "ingested"}
    mock_ingest.return_value.build_gold.return_value = 0

    assert main([str(path), "--scraped-at", "2026-08-31T12:00:00Z", "--source", "backfill"]) == 0
    kwargs = mock_ingest.return_value.ingest.call_args.kwargs
    assert (kwargs["scraped_at"], kwargs["source"], kwargs["completed"]) == (SCRAPED_AT, "backfill", True)
    mock_ingest.return_value.build_gold.assert_called_once()
    mock_sync.assert_called_once_with(mock_ingest.return_value.postgres_config)


@patch("scrapers.service.silver_cleaning.classification_ingest.sync_gold_if_configured")
@patch("scrapers.service.silver_cleaning.classification_ingest.ClassificationIngest")
def test_main_does_not_sync_when_the_gold_build_fails(mock_ingest, mock_sync, tmp_path):
    path = tmp_path / "av_jobs.jsonl"
    path.write_text(json.dumps(job()) + "\n", encoding="utf-8")
    mock_ingest.return_value.ingest.return_value = {"status": "ingested"}
    mock_ingest.return_value.build_gold.return_value = 1

    assert main([str(path), "--scraped-at", "2026-08-31T12:00:00Z"]) == 1
    mock_sync.assert_not_called()


@patch("scrapers.service.silver_cleaning.classification_ingest.ClassificationIngest")
def test_main_fails_without_building_gold_on_a_bad_file(mock_ingest, tmp_path):
    path = tmp_path / "av_jobs.jsonl"
    path.write_text(json.dumps({**job(), "deduplication_key": "bad"}) + "\n", encoding="utf-8")

    assert main([str(path), "--scraped-at", "2026-08-31T12:00:00Z", "--skip-gold"]) == 1
    mock_ingest.return_value.build_gold.assert_not_called()
