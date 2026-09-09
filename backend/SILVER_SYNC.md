# BE-9: backend integration (development stage)

See [review follow-up and API screenshot](evidence/README.md) for the refactoring
checklist and a reproducible snapshot using isolated synthetic data.

The API reads backend tables, not the staging schema. The data path is:

`silver.cleaned_job_postings -> manual sync -> company / jobposting / location / job_location / skill / job_skill / category / job_category -> API`

## Schema and migration

Each ORM entity has its own file in `app/models/`, including the junction tables.
The job router handles HTTP parameters and 404 responses; filtering, sorting,
pagination and response assembly live in `app/services/job.py`.
Shared identifier validation and text normalization live in `app/utils/`.

The three manual commands retain their existing module names. They use shared
CLI helpers (`app/utils/cli.py`) and delegate workflow execution to
`app/services/silver_pipeline.py`: sync jobs -> validate handoff -> import
categories. The pipeline owns sessions, transactions and writer locking;
record-level behavior remains in the individual services.

The logical ERD is in `Document/erd-job-categorizing/schema_silver.dbml`.
Its `silver` namespace describes the normalized logical layer; the backend's
physical ORM tables retain their existing names and default database schema.
The existing PDF diagram has not yet been regenerated.

For an existing backend database, back it up, stop writers, and apply
`app/sql/be9_migration.sql` with psql (`-v ON_ERROR_STOP=1`). Do not apply it to
the scraper database unless that database deliberately also hosts the backend.
The migration is repeatable, preserves rows, adds junction tables and relaxes
constraints for optional source fields. Legacy naive `posted_date` values are
interpreted as UTC. Confirm that convention before migrating an existing deployment.
Fresh databases use the normal ORM `init_db()` startup path.

`JobPosting.job_location` remains a compatibility display field. New consumers
use `locations`; no country/city is guessed from a free-text location label.
Salary and seniority are not inferred. Existing company metadata is preserved;
new companies have null URLs/type and `datasource_status=unverified`.

## Manual development refresh

From `backend/`, configure `DATABASE_URL` for the backend and
`SILVER_DATABASE_URL` for the source database in the ignored local environment.
Keep `SEED_ON_STARTUP=false`: the legacy seed command can replace company data.
Build the Silver dbt model first, then run:

```sh
python -m app.sync_silver --allow-unclassified
```

This flag is intentionally required. The current staging table is not guaranteed
AV-only. This command is for development, not production publication. Harshil's
classification output contract is still pending; this PR does not invent category
labels from descriptions, classify AV relevance, or delete non-AV jobs itself.

The CLI streams source rows and commits the destination as one transaction.
Concurrent CLI executions serialize via a PostgreSQL advisory lock. A bad row
rolls back the whole batch. Success reports read/created/updated counts; compare
their sum with source count and spot-check `source_key`, titles and locations.
No absent-source deletion is performed: job expiry/removal needs an agreed policy.
An empty input leaves the destination unchanged. The stable backend UUID survives
reruns when the upstream deduplication key is unchanged. Changes to upstream key
generation require an explicit identity reconciliation before syncing.

`SilverSync.run()` does not commit: library callers must provide a transaction
and serialize concurrent writers. `locations` is an array. Optional `skills`
contains `{name, skill_type}` objects with the five existing allowed skill types.
Missing `skills` preserves existing associations; an explicit empty array clears
them. The current dbt model does not produce skills yet, so an extraction/enrichment
step is still required before this is a complete skills pipeline. No LLM requests
or credentials are used by this sync command.

## External classification handoff: identity preflight

Run `python -m app.validate_handoff handoff.json` from `backend/` with the
backend `DATABASE_URL`. This read-only command validates a JSON array, reports
backend UUIDs, and exits unsuccessfully on missing, conflicting, ambiguous, or
duplicate targets. It does not import classifications or apply the AV gate.

Preferred record: `{"deduplication_key": "<exact Silver key>", "functional_area": "Perception"}`.
Fallback record: `{"source_job_id": "42", "ats_name": "greenhouse"}`.
Identifiers must be strings, preserving leading zeros and case. A supplied
deduplication key must match; a failed key lookup never falls back silently.
Additional source identifiers must agree with the matched job.

The current upstream key is **MD5 text, not a GUID**:
`scrapers/dbt/models/silver/cleaned_job_postings.sql` selects
`md5(natural_key) as deduplication_key`. It is a 32-character hexadecimal string.
Backend `job_id` is a separate generated UUID; `source_key` retains the exact
upstream key with a `silver:` prefix. Identity tests use representative MD5-shaped
keys. Do not cast or regenerate them as UUIDs: that would change the integration
contract. The resolver treats the upstream key as opaque non-empty text so a
future key-format migration can be reconciled explicitly.

Backend `job_id` is an internal UUID. External `job_id` is not automatically
interpreted: if the producer confirms it is an ATS identifier, rename it to
`source_job_id` and include `ats_name`. Never join using `bronze_id`; it is
run-dependent provenance only. Even ATS + ID can collide between company boards;
ambiguous matches require the Silver key. Jobs without source IDs use that key.

## Category import rule (initial taxonomy version 1)

Apply `app/sql/be9_migration.sql` to an existing backend first. Fresh databases
create Category and JobCategory through ORM startup. To import a handoff after
identity preflight, run `python -m app.import_categories handoff.json`.
The CLI commits the entire batch or rolls it back and uses the same PostgreSQL
advisory lock as Silver sync. Library callers must supply a transaction and
serialize writers. SilverSync also accepts the same inline classification fields.

`functional_area` is one label string or an array of strings. Each label becomes
Category.sub_type; main_type stays null because no parent taxonomy has been
provided. Labels are NFKC-normalized, whitespace-collapsed and casefolded for
uniqueness within taxonomy_version (positive integer, default 1). The first
cleaned spelling is kept for display. Synonyms are not guessed; commas, slashes
and other punctuation do not split a label. Use an array for multiple categories.
Labels from the producer are provisional categories, not a curated allowlist.

JobCategory stores the many-to-many foreign-key association. An explicit value
replaces all current associations for that job, including older taxonomy versions;
missing functional_area preserves them, [] clears them, and null/blank/invalid
labels reject the whole batch. Unlinked categories are retained. No confidence
score is inferred or imported. The logical ERD reserves it for future enrichment.
The preflight validates these labels and reports ready_to_import without writes.

Example: `{"deduplication_key":"<exact Silver key>","functional_area":["Perception","Controls"],"taxonomy_version":1}`.
This imports supplied labels only; AV relevance gating and frontend wiring remain
separate work. A later curated taxonomy needs explicit mapping/version migration.

## Job endpoints

- `GET /api/v1/jobs`: `q`, `company_id`, `location`, `skill`, `employment_type`,
  `category_id`, `page`, `page_size` (max 100).
- `GET /api/v1/jobs/{job_id}`: returns 404 for an unknown UUID.
- Existing company job counts now include synced rows.

Response fields: `job_id`, `title`, `company_id`, `company_name`, `locations`,
`skills`, `employment_type` (existing integer enum), `raw_description`, `source_url`,
`posted_date`, `categories` (category_id, main_type, sub_type, taxonomy_version).
Pagination is `{items,total,page,page_size,total_pages}`.
Location/skill filters use EXISTS semantics so multiple associations do not inflate
counts. Ordering is posted date descending then UUID for stable page boundaries.

Frontend pages still use mock data and must be wired to this API after agreeing
their nullable-field/category contract. Market Trends aggregates, LLM skill
extraction, and final classified-data integration are not completed by this slice.

## Tests

```sh
python -m pytest tests -q
```

Set `DATABASE_URL=sqlite://` for isolated API/service tests. Set
`BE9_TEST_POSTGRES=1` to additionally test the migration against local PostgreSQL
using `scrapers/.env`; that test creates and removes only a uniquely named test
schema. It never modifies the backend's public tables.
