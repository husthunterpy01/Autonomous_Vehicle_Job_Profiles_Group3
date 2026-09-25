-- Rolls back doc13_skill_trend_migration.sql. Repeatable.
-- WARNING: drops the skill trend history. Backfilled months would have to be
-- reloaded from MinIO, and live months cannot be recovered at all.
BEGIN;

DROP VIEW IF EXISTS gold.skill_trend_monthly;
DROP TABLE IF EXISTS gold.fact_job_skill_month;
DROP TABLE IF EXISTS gold.dim_job;
DROP TABLE IF EXISTS gold.dim_skill;
DROP TABLE IF EXISTS gold.dim_company;
DROP TABLE IF EXISTS gold.dim_month;
DROP TABLE IF EXISTS gold.scrape_run;

-- Remove the gold schema only if nothing else lives in it.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_class AS c
        JOIN pg_namespace AS n ON n.oid = c.relnamespace
        WHERE n.nspname = 'gold'
    ) THEN
        DROP SCHEMA IF EXISTS gold;
    END IF;
END $$;

-- Earlier drafts of this PR created these in the default schema. They were
-- only ever applied locally; drop them too in case one was.
DROP VIEW IF EXISTS skill_trend_monthly;
DROP TABLE IF EXISTS job_skill_observation;
DROP TABLE IF EXISTS scrape_run;

COMMIT;
