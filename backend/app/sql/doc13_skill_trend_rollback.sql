-- Rolls back doc13_skill_trend_migration.sql. Repeatable.
-- WARNING: drops the skill trend history. Backfilled months would have to be
-- reloaded from MinIO, and live months cannot be recovered at all.
BEGIN;
DROP VIEW IF EXISTS skill_trend_monthly;
DROP TABLE IF EXISTS job_skill_observation;
DROP TABLE IF EXISTS scrape_run;
COMMIT;
