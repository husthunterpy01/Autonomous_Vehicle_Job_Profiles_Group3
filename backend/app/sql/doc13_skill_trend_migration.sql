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

-- One row per scrape run, live or backfilled from MinIO. Only a completed
-- run writes observations; a failed or partial run is registered with
-- completed = false and nothing else, so it can never become a month's
-- snapshot or move last_seen_at.
CREATE TABLE IF NOT EXISTS scrape_run (
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
-- Columns added after the first draft, so re-running upgrades an early copy.
ALTER TABLE scrape_run ADD COLUMN IF NOT EXISTS completed boolean NOT NULL DEFAULT false;
ALTER TABLE scrape_run ADD COLUMN IF NOT EXISTS classifier_version text;

-- One row per (month, AV job, skill): "this job listed this skill in this
-- month", with the first and last completed run that saw it. Repeated runs
-- in the same month only move first/last seen, so rows grow with
-- jobs x skills per month, not with the number of runs.
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
CREATE INDEX IF NOT EXISTS ix_job_skill_observation_month_last_seen
    ON job_skill_observation (month, last_seen_at);

-- Monthly skill demand from a month-end snapshot: each month is compared by
-- the jobs in its latest completed run, as agreed in review. A job belongs to
-- that snapshot exactly when its last_seen_at equals the run's scraped_at.
-- Recreated rather than replaced so the column list can change between drafts.
DROP VIEW IF EXISTS skill_trend_monthly;
CREATE VIEW skill_trend_monthly AS
WITH month_snapshot AS (
    SELECT date_trunc('month', scraped_at AT TIME ZONE 'UTC')::date AS month,
           max(scraped_at) AS snapshot_at
    FROM scrape_run
    WHERE completed
    GROUP BY 1
),
snapshot_rows AS (
    SELECT o.month, o.deduplication_key, o.skill_normalized_name, o.skill_type,
           s.snapshot_at
    FROM job_skill_observation AS o
    JOIN month_snapshot AS s
      ON s.month = o.month
     AND o.last_seen_at = s.snapshot_at
),
per_skill AS (
    SELECT month, snapshot_at, skill_normalized_name, skill_type,
           count(DISTINCT deduplication_key) AS job_count
    FROM snapshot_rows
    GROUP BY month, snapshot_at, skill_normalized_name, skill_type
),
per_month AS (
    SELECT month, count(DISTINCT deduplication_key) AS jobs_with_skills
    FROM snapshot_rows
    GROUP BY month
)
SELECT s.month,
       s.snapshot_at,
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
