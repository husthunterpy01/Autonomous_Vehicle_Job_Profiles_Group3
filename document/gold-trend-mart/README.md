# Gold Trend Mart

Trend tables derived from the Silver layer after each scrape. The schema is in
`schema_gold.dbml` (rendered as `gold.pdf`). Gold tables are decoupled from
Silver: they hold plain reference values rather than foreign keys, so rebuilding
Silver or the backend's job tables never deletes trend history.

## Skill demand over time (DOC-13, #132)

**Status: design draft for review.** Migration:
`backend/app/sql/doc13_skill_trend_migration.sql`, rollback:
`backend/app/sql/doc13_skill_trend_rollback.sql`.

### Goal

Show how demand for each skill changes month by month, e.g. a "top 10 skills"
rank chart in the style of GitHub's *Top 10 programming languages 2023–2025*.
Martin has scrape runs from August onwards in MinIO to backfill it.

### Why the current schema can't do this

- `job_skill` links a job to a skill with no time information.
- `jobposting.ingested_at` (and Bronze's `ingested_at`) is overwritten on every
  run, and Silver keeps one row per job, so the database never holds history.
- `job_id` is not stable: a full re-import recreates every job, and `job_skill`
  rows cascade-delete with their job. `seed_companies.sql` also runs
  `TRUNCATE company CASCADE`.

### Tables

| Object | Grain | Purpose |
|---|---|---|
| `scrape_run` | one row per scrape run | Records every run (live or backfill), whether it completed, and the classifier version. Reloading a run is a no-op, and the latest completed run of each month is that month's snapshot |
| `job_skill_observation` | one row per (month, AV job, skill) | The history: this job listed this skill in this month, with the first and last completed run that saw it |
| `skill_trend_monthly` (view) | one row per (month, skill) | From each month's snapshot: distinct job count, share of the month's jobs, and a per-month rank |

No foreign keys to `jobposting`, `skill` or `company`, on purpose (see above).

### Decisions

1. **Stable key: Silver `deduplication_key`.** It is the md5 of the natural key,
   which prefers the source ATS job id, then the job URL, so the same posting
   keeps the same key across scrapes and re-imports. It is also what the backend
   already uses for identity (`source_key = "silver:" + deduplication_key`).
2. **Skill identity: `(normalized name, skill_type)` by value**, the same pair the
   `skill` table is unique on, normalized with `app.utils.normalization.normalized`.
   Storing the value instead of `skill_id` means rebuilding the `skill` table
   doesn't orphan history. The view joins back to `skill` for the display name
   and falls back to the normalized name.
3. **Time grain: calendar month, UTC.** The monthly chart is the target. Storing
   per month rather than per run keeps the table small: it grows with
   jobs × skills per month, not with the number of runs.
4. **Counting rule: month-end snapshot** (agreed in review). Each month is compared
   by the AV jobs in its **latest completed run**: a job is in that snapshot when
   its `last_seen_at` equals the run's `scraped_at`. Every month is one
   consistent snapshot, produced by a single classifier version and independent
   of how many runs the month had. A job still open next month counts again
   there, so the numbers mean *open postings at month end*. The table keeps
   first/last seen for the whole month, so switching to "open at any time during
   the month" later would only change the view.
5. **AV jobs only.** Only jobs that passed the relevance filter in that run are
   written, so the trend matches what the site shows.
6. **Rank: `row_number()` per month by job count, ties broken by name.** Every rank
   is unique, so two chart lines never share a position. The raw `job_count` and
   `share` are there if the frontend prefers ties.
7. **`share` for comparing months.** The number of open AV jobs changes from month to
   month, so `share = job_count / jobs_with_skills` compares better than raw
   counts. `jobs_with_skills` only counts snapshot jobs with at least one
   recognized skill, which is almost all of them.
8. **Retention: keep everything.** At about 1,800 AV jobs × about 8 skills, that's
   roughly 15k rows (a few MB) per month, well within the Supabase free tier.
   Finer per-run detail stays in MinIO if it's ever needed.

### Loading

For every scrape run, live or backfilled, after relevance classification and
skill extraction, in **one transaction**:

```sql
-- 1. Register the run; if it was already loaded, stop here.
INSERT INTO scrape_run (scraped_at, source, classifier_version, jobs_seen)
VALUES (:scraped_at, :source, :classifier_version, :jobs_seen)
ON CONFLICT (scraped_at) DO NOTHING
RETURNING run_id;

-- 2. Completed runs only: one upsert per (AV job, skill) in the run.
INSERT INTO job_skill_observation
    (month, deduplication_key, skill_normalized_name, skill_type, first_seen_at, last_seen_at)
VALUES (date_trunc('month', :scraped_at AT TIME ZONE 'UTC')::date,
        :deduplication_key, :skill_normalized_name, :skill_type, :scraped_at, :scraped_at)
ON CONFLICT (month, deduplication_key, skill_normalized_name, skill_type) DO UPDATE SET
    first_seen_at = least(job_skill_observation.first_seen_at, excluded.first_seen_at),
    last_seen_at  = greatest(job_skill_observation.last_seen_at, excluded.last_seen_at);

-- 3. Mark it completed.
UPDATE scrape_run SET completed = true WHERE run_id = :run_id;
```

- **Only completed runs write observations.** A failed or partial run (e.g. some
  sources didn't scrape) is registered with `completed = false` and nothing else,
  so it can't become a month's snapshot or move `last_seen_at`.
- **Idempotent and order-independent.** Reloading a run is a no-op, and runs can
  be backfilled in any order (`least`/`greatest` keep first/last seen right).
- **Past months are never rewritten.** When the classifier version changes, earlier
  months keep what they recorded, and `scrape_run.classifier_version` explains
  any step in the chart.

Skills come from
stage 7 enrichment, which is keyword-first: jobs covered by the keyword
vocabulary get categories and skills without an LLM call
(`KeywordCategoryClassifier` / `KeywordSkillExtractor`), and only the rest fall
back to Groq, which returns skills too. So a backfill does cost Groq tokens, for
the stage 6 mid-band and the stage 7 fallback. The classification cache below
limits that to jobs that are new or have changed.

### Classification cache (pipeline)

Agreed in review: build this **before the backfill**. It has two benefits:

- **Consistency, the main reason.** Re-running the LLM on the same job doesn't
  reliably return the same skills, even with `GROQ_TEMPERATURE=0`: stage 7 batches
  several jobs per prompt, so a job can land in a different batch each run, and
  the hosted model gets updated. A job's skills would then drift between months,
  and the trend would compare different extractions rather than real changes.
  With the cache, a posting keeps its first result for as long as its text and
  the classifier version stay the same.
- **Cost.** Jobs that were already classified skip stages 5–7, so only new or
  changed jobs pay for Groq.

- **Cache key:** `deduplication_key` plus a hash of the job title and description,
  so a posting whose text is edited is re-processed instead of reusing a stale
  result.
- **Stored per job:** relevance decision, categories, skills, and the classifier or
  prompt version that produced them.
- **Invalidation:** when the classifier, prompt or keyword vocabulary changes (for
  example #129 adding Infrastructure), bump the version and re-process
  everything once.
- **Flow:** before stages 5–7, look up each job. On a hit, reuse the stored result;
  otherwise run the stages and store the result. Only new or changed jobs pay
  for Groq.
- **Filter skills before caching.** The LLM sometimes returns unwanted or
  meaningless skills, and the cache would freeze them. Keep only skills that map
  to the known skill vocabulary / normalization list, and drop the rest before
  the result is stored.
- **Trend still records every job:** `load_gold` writes an observation for every AV
  job seen in the run, cached or new. Skipping cached jobs there would make the
  trend count only new postings.

A cache table would be `classification_cache (deduplication_key, content_hash,
classifier_version, is_av_relevant, categories, skills, classified_at)` with
primary key `(deduplication_key, content_hash, classifier_version)`. It belongs
to the pipeline, not the Gold schema, and the Gold tables work the same with or
without it.

### Reading: data for the rank chart

Top 10 skills of the latest month, with their rank in every month:

```sql
WITH latest AS (SELECT max(month) AS m FROM skill_trend_monthly),
top AS (
    SELECT skill_normalized_name, skill_type
    FROM skill_trend_monthly, latest
    WHERE month = latest.m AND rank <= 10
)
SELECT t.month, t.snapshot_at, t.skill_name, t.rank, t.job_count, t.share
FROM skill_trend_monthly AS t
JOIN top USING (skill_normalized_name, skill_type)
ORDER BY t.month, t.rank;
```

A skill that was outside the top 10 earlier shows its lower rank in those months,
so it enters the chart from below, like the GitHub chart.

### Validation done

Checked on local PostgreSQL 16 in isolated, disposable schemas:

- The migration applies twice, and upgrades the first draft in place (adds the
  new `scrape_run` columns, recreates the view, keeps existing rows).
- The rollback applies twice and leaves `skill` untouched; the migration
  re-applies after rollback.
- Loader: reloading a run is a no-op; runs loaded out of order keep first/last
  seen correct; a partial run registers without writing observations.
- The month-end snapshot uses only the latest completed run of each month. In
  the test, August counts only the 20 Aug run: jobs seen only on 5 Aug and a
  partial run on 28 Aug are excluded.
- The view and the rank-chart query return the expected counts, shares and
  ranks, including an unknown skill falling back to its normalized name.
- The checks reject a month that isn't the 1st, a seen time outside its month, a
  malformed key and an unknown source.

### Decided in review

- **Build the classification cache before the backfill** (consistency first,
  tokens second), and filter LLM skills against the vocabulary before caching.
- **Compare months by their latest completed run** (month-end snapshot). Past
  months are never rewritten, and `scrape_run.classifier_version` records which
  version produced each run.

### Open questions

1. **Month boundary.** UTC or Australia/Perth? UTC is simpler, and only runs near
   midnight on the last day of a month are affected.
2. **Where the live pipeline writes.** Proposed: a new `load_gold` step in the
   backend import, right after `import_skills`, into the same Supabase database.
   To confirm: does the job sync delete jobs that disappeared from the latest
   scrape? If it does, a one-statement snapshot of `job_skill` after the import
   would also work.

### Follow-ups (not in DOC-13)

- Backend endpoint serving the rank-chart data.
- Frontend rank chart on Market Trends (currently prototype data).
- The same pattern could replace `CategoryTrendSnapshot` for category trends.

## Regenerating `gold.pdf`

```bash
npx --yes @softwaretechnik/dbml-renderer -i schema_gold.dbml -f svg -o gold.svg
```

Then print the SVG to a single-page PDF, e.g. by wrapping it in an HTML page with
an `@page` size matching the SVG and running headless Chrome/Edge with
`--print-to-pdf --no-pdf-header-footer`.
