-- DOC-13: skill demand over time (Gold trend mart). Design draft for review.
-- Repeatable and non-destructive: creates new objects only, touches no
-- existing table. Rollback: doc13_skill_trend_rollback.sql.
--
-- These tables deliberately have NO foreign key to jobposting or skill:
-- a full re-import recreates every job (new job_id), and
-- seed_companies.sql runs TRUNCATE company CASCADE. Keying the history on
-- the Silver deduplication_key and the skill's normalized name keeps it
-- intact through both. See document/gold-trend-mart/README.md.
BEGIN;

-- One row per scrape run that fed the trend, live or backfilled from MinIO.
-- Lets the loader skip a run it has already loaded, and shows how many runs
-- (i.e. how much coverage) each month has.
CREATE TABLE IF NOT EXISTS scrape_run (
    run_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    scraped_at timestamptz NOT NULL UNIQUE,
    source varchar(16) NOT NULL DEFAULT 'live',
    jobs_seen integer,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT ck_scrape_run_source CHECK (source IN ('live', 'backfill')),
    CONSTRAINT ck_scrape_run_jobs_seen CHECK (jobs_seen IS NULL OR jobs_seen >= 0)
);

-- One row per (month, AV job, skill): "this job listed this skill at least
-- once during this month". Repeated scrapes in the same month update
-- first/last seen instead of adding rows, so a job counts once per month.
CREATE TABLE IF NOT EXISTS job_skill_observation (
    month date NOT NULL,
    deduplication_key text NOT NULL,
    skill_normalized_name text NOT NULL,
    skill_type varchar(64) NOT NULL,
    first_seen_at timestamptz NOT NULL,
    last_seen_at timestamptz NOT NULL,
    PRIMARY KEY (month, deduplication_key, skill_normalized_name, skill_type),
    CONSTRAINT ck_job_skill_observation_month_start
        CHECK (month = date_trunc('month', month)::date),
    CONSTRAINT ck_job_skill_observation_key
        CHECK (deduplication_key ~ '^[0-9a-f]{32}$'),
    CONSTRAINT ck_job_skill_observation_seen_order
        CHECK (first_seen_at <= last_seen_at),
    CONSTRAINT ck_job_skill_observation_seen_in_month
        CHECK (
            date_trunc('month', first_seen_at AT TIME ZONE 'UTC')::date = month
            AND date_trunc('month', last_seen_at AT TIME ZONE 'UTC')::date = month
        )
);

CREATE INDEX IF NOT EXISTS ix_job_skill_observation_skill_month
    ON job_skill_observation (skill_normalized_name, skill_type, month);

-- Monthly skill demand: how many distinct AV jobs listed each skill, the
-- share of that month's jobs, and a per-month rank for the bump chart.
-- Ties break on name so every rank is unique and a chart line never
-- collides with another.
CREATE OR REPLACE VIEW skill_trend_monthly AS
WITH per_skill AS (
    SELECT month, skill_normalized_name, skill_type,
           count(DISTINCT deduplication_key) AS job_count
    FROM job_skill_observation
    GROUP BY month, skill_normalized_name, skill_type
),
per_month AS (
    SELECT month, count(DISTINCT deduplication_key) AS jobs_with_skills
    FROM job_skill_observation
    GROUP BY month
)
SELECT s.month,
       coalesce(sk.skill_name, s.skill_normalized_name) AS skill_name,
       s.skill_normalized_name,
       s.skill_type,
       s.job_count,
       m.jobs_with_skills,
       round(s.job_count::numeric / m.jobs_with_skills, 4) AS share,
       row_number() OVER (
           PARTITION BY s.month
           ORDER BY s.job_count DESC, s.skill_normalized_name, s.skill_type
       ) AS rank
FROM per_skill AS s
JOIN per_month AS m USING (month)
LEFT JOIN skill AS sk
       ON sk.normalized_name = s.skill_normalized_name
      AND sk.skill_type = s.skill_type;

COMMIT;
