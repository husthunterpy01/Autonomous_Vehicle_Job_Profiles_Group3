# Bronze data layer

The Bronze layer is the append-only source of truth for job objects collected
by the scraper package. It stores each raw ATS job dictionary returned by
`fetch_jobs()` immediately before normalization.

## Location and partitioning

Generated records use this repository-relative layout:

```text
data/bronze/
└── <company-slug>/
    └── YYYY-MM-DD/
        └── <UTC-timestamp>_<record-id>.json
```

For example:

```text
data/bronze/stack-av/2026-08-21/
└── 20260821T041530.123456Z_550e8400-e29b-41d4-a716-446655440000.json
```

Generated company and date directories are ignored by Git. This README is the
only file under `data/bronze/` that should be committed.

## Record schema

Each UTF-8 JSON file contains exactly one record:

```json
{
  "record_id": "550e8400-e29b-41d4-a716-446655440000",
  "source_company": "Stack AV",
  "source_url": "https://job-boards.greenhouse.io/stackav/jobs/123",
  "scrape_timestamp": "2026-08-21T04:15:30.123456Z",
  "raw_payload": {
    "id": 123,
    "title": "Software Engineer"
  }
}
```

- `record_id` is a new UUID for every captured job object.
- `source_company` is the scraper's canonical company name.
- `source_url` is read from the raw ATS object.
- `scrape_timestamp` is a validated, canonical UTC timestamp for the scrape run.
- `raw_payload` is the unmodified job dictionary returned by `fetch_jobs()`.

The scraper does not clean, rename, decode, classify, sanitize, or deduplicate
`raw_payload` before writing it. Bronze preserves the decoded JSON job object,
not the byte-for-byte HTTP response body or discarded batch response envelope.

## Immutability and duplicate captures

Every capture is written completely to a same-directory `.tmp` file, flushed to
disk, and then atomically published as a new UUID-named JSON file using a
no-overwrite operation. Temporary files do not match the Silver layer's
`*.json` discovery pattern. Existing records are never updated or overwritten.
Re-scraping a posting is intentional: downstream processing can identify
captures using `source_url` together with `scrape_timestamp`, and can apply its
own duplicate or sanitization rules in the Silver layer.

## Silver-layer reading contract

A Silver transformation should recursively read `data/bronze/**/*.json`, skip
this README, validate the four metadata fields, and transform only the value of
`raw_payload`. Readers must not rely on directory iteration order; use
`scrape_timestamp` and `record_id` when deterministic ordering is required.

If a scrape or write is incomplete, the scraper logs the company, URL or job
identifier, timestamp/context, and exception. Successfully closed Bronze files
remain valid append-only records; failed normalized runs do not overwrite the
previous normalized output.
