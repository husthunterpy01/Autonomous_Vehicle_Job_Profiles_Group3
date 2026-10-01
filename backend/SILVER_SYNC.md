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

The logical ERD is in `document/erd-job-categorizing/schema_silver.dbml`.
Its `silver` namespace describes the normalized logical layer; the backend's
physical ORM tables retain their existing names and default database schema.
The existing PDF diagram has not yet been regenerated.

For an existing backend database, back it up, stop writers, and apply
`app/sql/be9_migration.sql` with psql (`-v ON_ERROR_STOP=1`). Do not apply it to
the scraper database unless that database deliberately also hosts the backend.
The migration is repeatable, preserves rows, adds junction tables and relaxes
constraints for optional source fields. Legacy naive `posted_date` values are
interpreted as UTC. Confirm that convention before migrating an existing deployment.
Fresh databases use the normal ORM `init_db()` startup path; the salary check
constraints are defined only in `app/sql/be13_salary_constraints_migration.sql`,
so apply that migration to a fresh database too.

Job locations are stored only in `location` + `job_location`; the legacy
`jobposting.job_location` text column was removed in BE-15 (apply
`app/sql/be15_drop_job_location_migration.sql` after `be9_migration.sql` on an
existing database). No country/city is guessed from a free-text location label.
Location arrays replace the previous
associations; an empty array, null, or missing field clears them, matching the
full Silver snapshot contract. False, numbers, strings and objects are invalid
and roll back the batch rather than silently clearing existing locations.
Seniority is not inferred. Salary (`salary_min`/`salary_max`/`salary_average`/
`salary_currency`/`salary_period`/`salary_source`; model, decisions and migrations
in `document/erd-job-categorizing/README.md`) is populated separately via `python -m
app.import_salary handoff.json` (`app/services/salary_sync.py`) - not part of
`SilverSync`/`sync_silver`, since the Silver staging table itself carries no
salary data for most ATS sources; see `scrapers/README.md` for how the
scraper pipeline derives it. Existing company metadata is preserved; new
companies have null URLs/type and `datasource_status=unverified`.

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
create Category and the job_category association table through ORM startup. To import a handoff after
identity preflight, run `python -m app.import_categories handoff.json`.
The CLI commits the entire batch or rolls it back and uses the same PostgreSQL
advisory lock as Silver sync. Library callers must supply a transaction and
serialize writers. SilverSync also accepts the same inline classification fields.

A record with `"functional_area": []` clears that job's categories. If no
backend job matches a *clear-only* record it is skipped (counted as
`skipped_unmatched_clears` in the result) instead of failing the batch - the
scrapers emit one for every job the pipeline drops, and most were never
inserted. A record that assigns categories to an unknown job is still an error.

`functional_area` is one label string or an array of strings. Each label becomes
Category.sub_type. main_type is never accepted from a record - it's a property
of the category, not of any individual job, so it comes only from the backend's
own static mapping at `app/config/category_main_types.yaml` (a hand-kept copy of
`scrapers/config/category_main_types.yaml`) and is looked up by normalized label
on every sync; a label with no entry there keeps main_type null. Labels are
NFKC-normalized, whitespace-collapsed and casefolded for uniqueness within
taxonomy_version (positive integer, default 1). The first cleaned spelling is
kept for display. Synonyms are not guessed; commas, slashes and other punctuation
do not split a label. Use an array for multiple categories. Labels from the
producer are provisional categories, not a curated allowlist.

job_category stores the many-to-many foreign-key association. An explicit value
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
`raw_description` is `null` on `GET /jobs` list items (the body is skipped there
for speed) and always a string on `GET /jobs/{job_id}` - not the same thing as a
job whose description is genuinely empty, which `GET /jobs/{job_id}` still
reports as `""`.
Pagination is `{items,total,page,page_size,total_pages}`.
Location/skill filters use EXISTS semantics so multiple associations do not inflate
counts. Ordering is posted date descending then UUID for stable page boundaries.

Frontend pages still use mock data and must be wired to this API after agreeing
their nullable-field/category contract. Market Trends aggregates, LLM skill
extraction, and final classified-data integration are not completed by this slice.

## Supabase mirror

When `SUPABASE_DATABASE_URL` is set in `backend/.env`, `sync_silver`,
`import_categories`, `import_skills`, and `import_salary` each automatically
push a full mirror (`scripts/sync_to_supabase.py`: `pg_dump --schema public`
locally, `pg_restore --clean --if-exists` into Supabase) after they succeed.
A mirror failure is logged, not raised - it never fails the command that
triggered it, since the local write already committed. Unset the variable to
disable mirroring; run `python -m scripts.sync_to_supabase` directly to sync
on demand without running an import. See the root README's "Supabase mirror"
section for setup (connection-pooler string, not the IPv6-only direct host).

## Known issue: missing/wrong locations, investigated 2026-10-01

Five distinct causes were found and traced to this level of confidence by
comparing `data/job_classification/av_jobs.jsonl`, the local database, the
live `silver.cleaned_job_postings` table, and Supabase directly against each
other. Four are fixed; one (closed/expired postings) has no fix available.

**1. Supabase mirror fell behind local - FIXED.** Supabase showed 305/1229
jobs across 26 companies missing `job_location` (worst: Applied Intuition
109/124). `sync_silver --allow-unclassified` reads `silver.cleaned_job_postings`
live and has no resume/skip logic of its own, so local stayed correct; the
Supabase mirror (`scripts/sync_to_supabase.py`) only updates when something
calls `sync_if_configured()` after a local write, and a mirror failure is
logged, not raised - so a mirror that silently stopped keeping up left
Supabase frozen on an older, smaller snapshot (1,229 Supabase jobs vs. 5,292
local) from before local had already picked up fuller Silver data. (Initially
misattributed to the classification pipeline's own resume-skip staleness in
`av_jobs.jsonl`, since the per-company numbers matched closely - that file
is real but unrelated: it never feeds `job_location`, only
`import_categories`/`import_skills`/`import_salary` via `handoff.json`.)
Fixed with `backend/scripts/backfill_job_locations.py`: reads Silver live
and updates `job_location` only for jobs that already exist in the target
database (matched by `source_key`), touching nothing a full `sync_silver`
run wouldn't. Run with `DATABASE_URL` pointed at Supabase to backfill it
directly without a full mirror push; preloads jobs/locations in bulk rather
than querying per Silver row, since the naive per-row version doesn't finish
in practical time against a remote pooler. Reduced Supabase's missing count
from 305 to 33, then to 14 once (2) and (5) below were also fixed and
re-propagated through the same two commands.

**2. Multi-location postings joined with `;` were stored as one location - FIXED.**
`cleaned_job_postings.sql` only split the raw bronze `location` field on `|`;
sources whose raw value used `;` (mostly Waymo) passed through unsplit, so
e.g. `"Mountain View, CA; San Francisco, CA; Kirkland, WA"` became a single
`location` row instead of three, making those jobs unmatchable by any one of
their real cities. Affected 192 jobs locally / 98 on Supabase before the
local<->Supabase gap in (1) was also fixed. Fixed by splitting on `'\s*[|;]\s*'`
instead of `'\s*\|\s*'`. Rebuild with `scrapers/script/run_silver_build.sh`,
then re-run `sync_silver` (local) and `backfill_job_locations.py` (Supabase)
to propagate.

**3. Fallback dedup-key included `locations` - FIXED, no observed impact
yet.** When a Silver row has neither `source_job_id` nor `job_url`, its
`deduplication_key` fell back to a hash of
`company_name|job_name|job_uploaded_at|locations`. Because `locations` is
part of that hash, a change to a job's extracted locations - including a fix
like (2) - re-hashes an otherwise-unchanged, still-live job under a new key,
orphaning the old backend row even though the real posting never went away.
Fixed by dropping `locations` from the fallback key. Confirmed zero current
rows use this fallback path (both `source_job_id` and `job_url` are null),
so this was a live structural risk, not (yet) an observed cause of any
specific orphan - see (4).

**4. Closed/expired postings - NOT FIXABLE.** 14 jobs (Applied Intuition 7,
Aurora 4, 42dot 2, TIER IV 1) exist in the backend with no current Silver row
at all - confirmed by searching Silver for their exact titles (zero matches
anywhere, any company). These aren't re-keyed or stale, they're gone: the
posting was removed from the company's career page sometime after it was
first imported, and nothing deletes/flags a `jobposting` row when its Silver
source disappears (see "No absent-source deletion is performed" above).
There is no data left anywhere to backfill from. A real fix here is a
job-expiry policy (e.g. flag or soft-delete a `jobposting` row once its
`deduplication_key` stops appearing in a Silver export for N consecutive
runs), not a backfill - not implemented.

Verified two ways, independently, for every one of the 14: (a) the live
source right now - queried Ashby's API directly for Applied
Intuition/Aurora/42dot (title-by-title against 313/84/88 current postings)
and fetched TIER IV's live careers page, zero matches; (b) our own last
archived MinIO response, read from the raw parquet before any of our code
touched it (`api/applied_intuition/applied_intuition_2026-09-29_*.parquet`,
HTTP 200, 312 jobs that day) - also zero matches. Both agree, which rules
out a bug on our side (pagination, a bad scrape, bronze/Silver mangling the
title): the company's own API had already stopped returning these postings
before we ever scraped the snapshot Silver is built from.

2 of the 13 that were on Ashby (Applied Intuition's "Software Engineer -
Mapping and Localization", 42dot's "System Framework Engineer") turned out
to not really be in this category: same title, but Ashby had reopened them
under a brand-new internal job ID, which this system treats as an entirely
different posting, not an update to the old one. The old `jobposting` row
is still correctly dead (that specific req closed); the new req already has
a correct, current Silver row (confirmed: real location data, e.g.
`Stuttgart`) but no `jobposting` row of its own yet, since nothing creates
new jobposting rows except a full `sync_silver` run, which can't be used
selectively without also importing every unclassified Silver row. Importing
just these 2 properly also means running them through classification first
(`job_classifier.py`/`job_enricher.py`), not just copying location data -
not done, left as a follow-up.

**5. TIER IV's scraper config had no location selector - FIXED.** Its
`html_sources` entry (`scrapers/data/ats_sources.yaml`) extracted title/
description/link but never `location`, unlike every other `ats: html`
company - the list page has no location anywhere in its HTML at all
(checked directly: no location/tag CSS class, no "勤務地" text). Confirmed
via `silver.cleaned_job_postings` that all 20 TIER IV rows had
`locations = '{}'`; every genuine API-based source (Greenhouse, Workday,
Ashby, Lever, SmartRecruiters, Workable, Comeet, Personio - 5,207 postings)
had 0% empty locations, so this was never a systemic extraction problem,
just a one-company config gap. The location does exist, but only on each
job's detail page, as `jobLocation.address` inside a schema.org `JobPosting`
JSON-LD block - and it's the same boilerplate bilingual employment-contract
address on every posting checked, not a distinct per-job value. Fixed by
teaching `RawFetch._attach_html_details`
(`scrapers/service/fetch/rawfetch.py`) to optionally also pull and
regex-clean a location from that JSON-LD (`detail: location: json_ld` in the
YAML config), generalizing it from a description-only mechanism to a
`{"description": ..., "location": ...}` map; `HTMLExtractor` already had a
“use the detail-page value only if the list page gave nothing” fallback
pattern for description, now applied to location too. Re-scraped for real
(not just tested): TIER IV went from 20/20 empty to 1/57 (one remaining is
a generic "career registration" entry with no real per-job detail page, not
an actual posting). Rolling this out required widening the
`x-bronze-detail` script's value shape from a bare description string to a
dict, which broke parsing of any already-archived-in-MinIO raw response
using the old shape (`bronze_ingest.py` replays every unprocessed archived
response, not just freshly-fetched ones) - `HTMLExtractor._detail_map` now
normalizes both shapes so older archived payloads keep working.

None of this is monitored - a mirror drifting again (1), a new delimiter
style showing up in bronze data (2), or a posting closing (4) would all
recur silently with no alert.

## Tests

```sh
python -m pytest tests -q
```

Set `DATABASE_URL=sqlite://` for isolated API/service tests. To also run the
PostgreSQL regression locally, set `BE9_TEST_POSTGRES=1` and
`BE9_TEST_DATABASE_URL=postgresql://...` to a test database whose user can create
schemas. The test falls back to DATABASE_URL if the dedicated URL is unset; it
never reads scrapers/.env. CI supplies the dedicated URL and enables the test.
The test creates and removes only a uniquely named schema. It verifies repeated
migration, preservation of legacy company/job rows, Text column type, and a real
Silver sync with more than 255 characters of locations. Public tables are untouched.
