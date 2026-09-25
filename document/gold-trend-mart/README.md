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
| `scrape_run` | one row per scrape run | Records which runs were loaded (live or backfill), so reloading a run is a no-op and each month's coverage is visible |
| `job_skill_observation` | one row per (month, AV job, skill) | The history: this job listed this skill at least once in this month, with first and last seen times |
| `skill_trend_monthly` (view) | one row per (month, skill) | Distinct job count, share of the month's jobs, and a per-month rank |

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
4. **Counting rule: distinct AV jobs per skill per month.** A job seen in several
   runs in the same month counts once, via the primary key. A job still open in
   the next month counts again there, so the numbers mean *active postings that
   month*, not *new postings*.
5. **AV jobs only.** Only jobs that passed the relevance filter in that run are
   written, so the trend matches what the site shows.
6. **Rank: `row_number()` per month by job count, ties broken by name.** Every rank
   is unique, so two chart lines never share a position. The raw `job_count` and
   `share` are there if the frontend prefers ties.
7. **`share` for comparing months.** Monthly volume varies (August starts
   mid-month, runs may be missed), so `share = job_count / jobs_with_skills`
   compares better across months than raw counts. `jobs_with_skills` only counts
   jobs with at least one recognized skill, which is almost all of them.
8. **Retention: keep everything.** At about 1,800 AV jobs × about 8 skills, that's
   roughly 15k rows (a few MB) per month, well within the Supabase free tier.
   Finer per-run detail stays in MinIO if it's ever needed.

### Loading

For every scrape run, live or backfilled, after relevance classification and
skill extraction:

```sql
-- 1. Register the run; if it was already loaded, stop here.
INSERT INTO scrape_run (scraped_at, source, jobs_seen)
VALUES (:scraped_at, :source, :jobs_seen)
ON CONFLICT (scraped_at) DO NOTHING
RETURNING run_id;

-- 2. One upsert per (AV job, skill) in the run.
INSERT INTO job_skill_observation
    (month, deduplication_key, skill_normalized_name, skill_type, first_seen_at, last_seen_at)
VALUES (date_trunc('month', :scraped_at AT TIME ZONE 'UTC')::date,
        :deduplication_key, :skill_normalized_name, :skill_type, :scraped_at, :scraped_at)
ON CONFLICT (month, deduplication_key, skill_normalized_name, skill_type) DO UPDATE SET
    first_seen_at = least(job_skill_observation.first_seen_at, excluded.first_seen_at),
    last_seen_at  = greatest(job_skill_observation.last_seen_at, excluded.last_seen_at);
```

Both steps are idempotent, so a backfill can be re-run safely. Skills come from
stage 7 enrichment, which is keyword-first: jobs covered by the keyword
vocabulary get categories and skills without an LLM call
(`KeywordCategoryClassifier` / `KeywordSkillExtractor`), and only the rest fall
back to Groq, which returns skills too. So a backfill does cost Groq tokens, for
the stage 6 mid-band and the stage 7 fallback. The classification cache below
limits that to jobs that are new or have changed.

### Optional: classification cache (pipeline optimisation)

The trend itself doesn't need this, but it saves Groq tokens on both the backfill
and daily runs: jobs that were already classified don't go through stages 5–7
again.

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
SELECT t.month, t.skill_name, t.rank, t.job_count, t.share
FROM skill_trend_monthly AS t
JOIN top USING (skill_normalized_name, skill_type)
ORDER BY t.month, t.rank;
```

A skill that was outside the top 10 earlier shows its lower rank in those months,
so it enters the chart from below, like the GitHub chart.

### Validation done

Checked on local PostgreSQL 16 in an isolated, disposable schema:

- The migration applies twice; the rollback applies twice and leaves `skill`
  untouched; the migration re-applies after rollback.
- Reloading an already-loaded run is a no-op. A job seen in two runs in the same
  month counts once, and its first/last seen times cover both runs.
- The view and the rank-chart query return the expected counts, shares and
  ranks, including an unknown skill falling back to its normalized name.
- The checks reject a month that isn't the 1st, a seen time outside its month, a
  malformed key and an unknown source.

### Open questions for review

1. **Classification cost for backfilled jobs.** Re-classifying every historical
   job costs Groq tokens (stage 6 mid-band and stage 7 fallback). The
   classification cache above would reuse existing results and only classify new
   or changed jobs. Build the cache before the backfill, or backfill first and add
   it later?
2. **Extractor changes shift the trend.** If the keyword list changes, later months
   are counted differently from earlier ones. Record an extractor version on
   `scrape_run`, or re-extract the whole history after a change?
3. **Month boundary.** UTC or Australia/Perth? UTC is simpler, and only runs near
   midnight on the last day of a month are affected.
4. **Where the live pipeline writes.** A new step after skill enrichment, next to
   `import_skills`, into the same Supabase database?

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
