from __future__ import annotations

import io
import json
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from minio import Minio
from minio.error import S3Error

from scrapers.config import MinioConfig
from scrapers.models.bronze.bronze_model import RawPayload

API_SOURCE = "api"
HTML_SOURCE = "html"
ALLOWED_SOURCES = {API_SOURCE, HTML_SOURCE}
PARQUET_CONTENT_TYPE = "application/vnd.apache.parquet"


class ResponseArchive:
    """Persist raw API JSON and HTML responses as Parquet objects in MinIO."""
    def __init__(self, minio_config: MinioConfig | None = None) -> None:
        self.minio_config = minio_config or MinioConfig()
        client_kwargs = {
            "endpoint": self.minio_config.endpoint,
            "access_key": self.minio_config.access_key,
            "secret_key": self.minio_config.secret_key,
            "secure": self.minio_config.secure,
        }
        if self.minio_config.region:
            client_kwargs["region"] = self.minio_config.region
        self.client = Minio(**client_kwargs)

    def _create_bucket(self) -> None:
        try:
            if not self.client.bucket_exists(self.minio_config.bucket):
                self.client.make_bucket(self.minio_config.bucket)
        except S3Error as exc:
            raise RuntimeError(
                f"MinIO rejected the request ({exc.code}) for bucket "
                f"{self.minio_config.bucket!r}. Check MINIO_ENDPOINT, "
                f"MINIO_ACCESS_KEY, MINIO_SECRET_KEY, and MINIO_SECURE."
            ) from exc

    def save_raw_response(
        self,
        company_name: str,
        collected_at: datetime,
        raw_response: Any,
        *,
        source: str | None = None,
        source_system: str | None = None,
        url: str = "",
        status: int = 200,
        content_type: str = "",
    ) -> str:
        """Write one API or HTML payload to a timestamped Parquet object.
        ``raw_response`` may be parsed JSON (``dict`` / ``list``), HTML text,
        or the original response bytes. API and HTML runs are stored under
        separate object prefixes so bronze files stay grouped by collection
        method.
        """
        if raw_response is None:
            raise ValueError("raw_response is required")

        resolved_source = self._resolve_source(source, raw_response, content_type)
        payload = RawPayload(
            source=resolved_source,
            company=company_name,
            source_system=source_system,
            url=url,
            status=status,
            content_type=content_type or self._default_content_type(resolved_source),
            body=self._encode_body(raw_response),
            fetched_at=self._as_utc(collected_at),
        )
        return self.save_payloads([payload])

    def save_payloads(self, payloads: Sequence[RawPayload]) -> str:
        """Write one or more bronze payloads to a single Parquet object."""
        if not payloads:
            raise ValueError("At least one raw payload is required")

        rows = [self._payload_to_row(payload) for payload in payloads]
        sources = {row["source"] for row in rows}
        companies = {row["company"] for row in rows}
        if len(sources) != 1 or len(companies) != 1:
            raise ValueError(
                "All payloads in one archive file must share the same source and company"
            )

        collected_at = max(row["fetched_at"] for row in rows)
        object_name = self._object_key(rows[0]["company"], rows[0]["source"], collected_at)
        parquet_bytes = self._to_parquet_bytes(rows)

        try:
            self._create_bucket()
            self.client.put_object(
                bucket_name=self.minio_config.bucket,
                object_name=object_name,
                data=io.BytesIO(parquet_bytes),
                length=len(parquet_bytes),
                content_type=PARQUET_CONTENT_TYPE,
            )
        except S3Error as exc:
            raise RuntimeError(
                f"MinIO rejected the request ({exc.code}) for bucket "
                f"{self.minio_config.bucket!r}. Check MINIO_ENDPOINT, "
                f"MINIO_ACCESS_KEY, MINIO_SECRET_KEY, and MINIO_SECURE."
            ) from exc
        return object_name

    def _list_objects(self, bucket_name: str, prefix: str = "") -> list[str]:
        return [
            obj.object_name
            for obj in self.client.list_objects(
                bucket_name=bucket_name,
                prefix=prefix,
                recursive=True,
            )
            if obj.object_name
        ]

    def _get_object_info(self, object_key: str) -> list[dict[str, Any]]:
        try:
            response = self.client.get_object(self.minio_config.bucket, object_key)
        except S3Error as exc:
            if exc.code in {"NoSuchKey", "NoSuchObject"}:
                raise ValueError(f"Object {object_key} not found") from exc
            raise

        try:
            table = pq.read_table(io.BytesIO(response.read()))
        except Exception as exc:
            raise ValueError(f"Failed to parse Parquet object {object_key}") from exc
        finally:
            response.close()
            response.release_conn()

        return table.to_pylist()

    @staticmethod
    def _to_parquet_bytes(rows: list[dict[str, Any]]) -> bytes:
        table = pa.Table.from_pylist(rows)
        buffer = io.BytesIO()
        pq.write_table(table, buffer)
        return buffer.getvalue()

    @staticmethod
    def _payload_to_row(payload: RawPayload) -> dict[str, Any]:
        source = payload.source.strip().lower()
        if source not in ALLOWED_SOURCES:
            raise ValueError(
                f"source must be one of {sorted(ALLOWED_SOURCES)}, got {payload.source!r}"
            )
        if not payload.company.strip():
            raise ValueError("company is required")

        return {
            "source": source,
            "company": payload.company,
            "source_system": payload.source_system,
            "url": payload.url,
            "status": int(payload.status),
            "content_type": payload.content_type,
            "body": ResponseArchive._decode_body(payload.body),
            "fetched_at": ResponseArchive._as_utc(payload.fetched_at),
        }

    def _extract_data_from_storage(self, bucket_name) :
        latest_by_company = {}
        for object_name in self._list_objects(bucket_name):
            if not object_name.endswith(".parquet"):
                continue
            scraped_components = object_name.split("/")
            if len(scraped_components) != 3:
                print(f"Unexpectsed number of components found in the archive log, please check the file {object_name}")
                continue

            source, company_name, filename = scraped_components
            key = (source, company_name)
            previous = latest_by_company.get(key)
            if previous is None or filename > previous[1]:
                latest_by_company[key] = (object_name, filename)

        for (source, company_name), (object_name, _) in latest_by_company.items():
            response = None
            try:
                response = self.client.get_object(bucket_name, object_name)
                response_data = response.read()
                response_df = pd.read_parquet(io.BytesIO(response_data))
                yield source, company_name, response_df
            except S3Error as exc:
                print(f"[skip] failed to read {object_name}: {exc}")
            finally:
                if response is not None:
                    response.close()
                    response.release_conn()

    @staticmethod
    def _object_key(company_name: str, source: str, collected_at: datetime) -> str:
        company_slug = company_name.lower().replace(" ", "_")
        stamp = ResponseArchive._as_utc(collected_at).strftime("%Y-%m-%d_%H-%M-%S")
        return f"{source}/{company_slug}/{company_slug}_{stamp}.parquet"

    @staticmethod
    def _resolve_source(
        source: str | None, raw_response: Any, content_type: str
    ) -> str:
        if source:
            resolved = source.strip().lower()
            if resolved not in ALLOWED_SOURCES:
                raise ValueError(
                    f"source must be one of {sorted(ALLOWED_SOURCES)}, got {source!r}"
                )
            return resolved

        lowered_type = content_type.lower()
        if "json" in lowered_type or isinstance(raw_response, (dict, list)):
            return API_SOURCE
        return HTML_SOURCE

    @staticmethod
    def _default_content_type(source: str) -> str:
        return "application/json" if source == API_SOURCE else "text/html"

    @staticmethod
    def _encode_body(raw_response: Any) -> bytes:
        if isinstance(raw_response, bytes):
            return raw_response
        if isinstance(raw_response, str):
            return raw_response.encode("utf-8")
        return json.dumps(raw_response, ensure_ascii=False, default=str).encode("utf-8")

    @staticmethod
    def _decode_body(body: bytes) -> str:
        return body.decode("utf-8", errors="replace")

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
