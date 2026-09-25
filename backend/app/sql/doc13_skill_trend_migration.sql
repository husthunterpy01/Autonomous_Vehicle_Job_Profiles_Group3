-- DOC-13: skill demand over time - Gold layer star schema. Design draft for review.
-- Repeatable and non-destructive: creates the gold schema and new objects
-- only, touching no existing table. Rollback: doc13_skill_trend_rollback.sql.
--
-- Gold is its own schema, loaded from each scrape run's pipeline output,
-- not from the backend's tables. It has no foreign keys into them, so
-- re-importing jobs (new job_id values) or seed_companies.sql's
-- TRUNCATE company CASCADE never touches it. Foreign keys only exist
-- inside the star (fact -> dimensions). See document/gold-trend-mart/README.md.
BEGIN;

CREATE SCHEMA IF NOT EXISTS gold;

-- Load log: one row per scrape run, live or backfilled from MinIO. Only a
-- completed run writes facts; a failed or partial run is registered with
-- completed = false and nothing else, so it can never become a month's
-- snapshot or move last_seen_at.
CREATE TABLE IF NOT EXISTS gold.scrape_run (
    run_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    scraped_at timestamptz NOT NULL UNIQUE,
    source varchar(16) NOT NULL DEFAULT 'live',
    completed boolean NOT NULL DEFAULT false,
    classifier_version text,
    jobs_seen integer,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT ck_scrape_run_source CHECK (source IN ('live', 'backfill')),
    CONSTRAINT ck_scrape_run_jobs_seen CHECK (jobs_seen IS NULL OR jobs_seen >= 0)
);

-- Dimension: calendar month (UTC). month_key is yyyymm, e.g. 202608.
CREATE TABLE IF NOT EXISTS gold.dim_month (
    month_key integer PRIMARY KEY,
    month_start date NOT NULL UNIQUE,
    year smallint NOT NULL,
    month smallint NOT NULL,
    label text NOT NULL,
    CONSTRAINT ck_dim_month_start CHECK (month_start = date_trunc('month', month_start)::date),
    CONSTRAINT ck_dim_month_parts CHECK (
        year = extract(year FROM month_start)
        AND month = extract(month FROM month_start)
        AND month_key = year * 100 + month
    )
);

-- Dimension: skill. Natural key (normalized_name, skill_type), normalized the
-- same way as the backend's skill table.
CREATE TABLE IF NOT EXISTS gold.dim_skill (
    skill_key bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    normalized_name text NOT NULL,
    skill_type varchar(64) NOT NULL,
    display_name text NOT NULL,
    CONSTRAINT uq_dim_skill_natural_key UNIQUE (normalized_name, skill_type)
);

-- Dimension: company. Natural key company_name.
CREATE TABLE IF NOT EXISTS gold.dim_company (
    company_key bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    company_name text NOT NULL UNIQUE,
    company_type text
);

-- Dimension: job. Natural key deduplication_key (md5 hex from the pipeline's
-- dedup step), which stays the same across scrapes and re-imports. Attributes
-- are type-1 (latest value wins); first/last seen let an out-of-order backfill
-- keep the newest attributes.
CREATE TABLE IF NOT EXISTS gold.dim_job (
    job_key bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    deduplication_key text NOT NULL UNIQUE,
    title text NOT NULL,
    main_type text,
    first_seen_at timestamptz NOT NULL,
    last_seen_at timestamptz NOT NULL,
    CONSTRAINT ck_dim_job_key CHECK (deduplication_key ~ '^[0-9a-f]{32}$'),
    CONSTRAINT ck_dim_job_seen_order CHECK (first_seen_at <= last_seen_at)
);

-- Fact: one row per (month, AV job, skill), "this job listed this skill in
-- this month", with the first and last completed run that saw it. Repeated
-- runs in a month only move first/last seen, so rows grow with
-- jobs x skills per month, not with the number of runs.
CREATE TABLE IF NOT EXISTS gold.fact_job_skill_month (
    month_key integer NOT NULL REFERENCES gold.dim_month (month_key),
    job_key bigint NOT NULL REFERENCES gold.dim_job (job_key),
    skill_key bigint NOT NULL REFERENCES gold.dim_skill (skill_key),
    company_key bigint NOT NULL REFERENCES gold.dim_company (company_key),
    first_seen_at timestamptz NOT NULL,
    last_seen_at timestamptz NOT NULL,
    PRIMARY KEY (month_key, job_key, skill_key),
    CONSTRAINT ck_fact_seen_order CHECK (first_seen_at <= last_seen_at),
    CONSTRAINT ck_fact_seen_in_month CHECK (
        extract(year FROM first_seen_at AT TIME ZONE 'UTC') * 100
            + extract(month FROM first_seen_at AT TIME ZONE 'UTC') = month_key
        AND extract(year FROM last_seen_at AT TIME ZONE 'UTC') * 100
            + extract(month FROM last_seen_at AT TIME ZONE 'UTC') = month_key
    )
);

CREATE INDEX IF NOT EXISTS ix_fact_job_skill_month_snapshot
    ON gold.fact_job_skill_month (month_key, last_seen_at);
CREATE INDEX IF NOT EXISTS ix_fact_job_skill_month_skill
    ON gold.fact_job_skill_month (skill_key, month_key);
CREATE INDEX IF NOT EXISTS ix_fact_job_skill_month_company
    ON gold.fact_job_skill_month (company_key);

-- Monthly skill demand from a month-end snapshot: each month is compared by
-- the jobs in its latest completed run. A fact belongs to that snapshot
-- exactly when its last_seen_at equals the run's scraped_at.
DROP VIEW IF EXISTS gold.skill_trend_monthly;
CREATE VIEW gold.skill_trend_monthly AS
WITH month_snapshot AS (
    SELECT (extract(year FROM scraped_at AT TIME ZONE 'UTC') * 100
            + extract(month FROM scraped_at AT TIME ZONE 'UTC'))::integer AS month_key,
           max(scraped_at) AS snapshot_at
    FROM gold.scrape_run
    WHERE completed
    GROUP BY 1
),
snapshot_facts AS (
    SELECT f.month_key, f.job_key, f.skill_key, s.snapshot_at
    FROM gold.fact_job_skill_month AS f
    JOIN month_snapshot AS s
      ON s.month_key = f.month_key
     AND f.last_seen_at = s.snapshot_at
),
per_skill AS (
    SELECT month_key, snapshot_at, skill_key, count(DISTINCT job_key) AS job_count
    FROM snapshot_facts
    GROUP BY month_key, snapshot_at, skill_key
),
per_month AS (
    SELECT month_key, count(DISTINCT job_key) AS jobs_with_skills
    FROM snapshot_facts
    GROUP BY month_key
)
SELECT p.month_key,
       m.month_start AS month,
       m.label AS month_label,
       p.snapshot_at,
       k.display_name AS skill_name,
       k.normalized_name AS skill_normalized_name,
       k.skill_type,
       p.job_count,
       t.jobs_with_skills,
       round(p.job_count::numeric / t.jobs_with_skills, 4) AS share,
       row_number() OVER (
           PARTITION BY p.month_key
           ORDER BY p.job_count DESC, k.normalized_name, k.skill_type
       ) AS rank
FROM per_skill AS p
JOIN per_month AS t USING (month_key)
JOIN gold.dim_month AS m USING (month_key)
JOIN gold.dim_skill AS k USING (skill_key);

COMMIT;
