from datetime import datetime, timezone
from io import BytesIO
from unittest.mock import patch

import pyarrow.parquet as pq

from scrapers.config.minio import MinioConfig
from scrapers.response_archive import ResponseArchive


@patch("scrapers.response_archive.Minio")
def test_save_raw_response_writes_api_parquet(mock_minio):
    stored = {}

    def put_object(**kwargs):
        stored["object_name"] = kwargs["object_name"]
        stored["bytes"] = kwargs["data"].read()
        stored["content_type"] = kwargs["content_type"]

    client = mock_minio.return_value
    client.bucket_exists.return_value = True
    client.put_object.side_effect = put_object
    archive = ResponseArchive(
        MinioConfig(
            endpoint="localhost:9000",
            access_key="test",
            secret_key="test",
            secure=False,
            bucket="test-bucket",
        )
    )
    collected_at = datetime(2026, 8, 30, 1, 0, 0, tzinfo=timezone.utc)

    object_name = archive.save_raw_response(
        "Stack AV",
        collected_at,
        [{"id": "1", "title": "Engineer"}],
        source="api",
        url="https://boards-api.greenhouse.io/v1/boards/stackav/jobs",
        content_type="application/json",
    )

    assert object_name == "api/stack_av/stack_av_2026-08-30_01-00-00.parquet"
    assert stored["content_type"] == "application/vnd.apache.parquet"
    rows = pq.read_table(BytesIO(stored["bytes"])).to_pylist()
    assert rows[0]["company"] == "Stack AV"
    assert rows[0]["source"] == "api"
    assert '"id": "1"' in rows[0]["body"]


@patch("scrapers.response_archive.Minio")
def test_save_raw_response_rejects_missing_body(mock_minio):
    archive = ResponseArchive(
        MinioConfig(
            endpoint="localhost:9000",
            access_key="test",
            secret_key="test",
            secure=False,
            bucket="test-bucket",
        )
    )

    try:
        archive.save_raw_response(
            "Stack AV",
            datetime.now(timezone.utc),
            None,
            source="api",
        )
    except ValueError as exc:
        assert "raw_response is required" in str(exc)
    else:
        raise AssertionError("expected ValueError")
