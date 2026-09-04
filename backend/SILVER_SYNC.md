# BE-9: backend integration (development stage)

The API reads backend tables, not the staging schema. The data path is:

`silver.cleaned_job_postings -> manual sync -> company / jobposting / location / job_location / skill / job_skill -> API`

## Schema and migration

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
labels, classify jobs, or delete non-AV jobs itself.

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

## API

- `GET /api/v1/jobs`: `q`, `company_id`, `location`, `skill`, `employment_type`,
  `page`, `page_size` (max 100).
- `GET /api/v1/jobs/{job_id}`: returns 404 for an unknown UUID.
- Existing company job counts now include synced rows.

Response fields: `job_id`, `title`, `company_id`, `company_name`, `locations`,
`skills`, `employment_type` (existing integer enum), `raw_description`, `source_url`,
`posted_date`. Pagination is `{items,total,page,page_size,total_pages}`.
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
