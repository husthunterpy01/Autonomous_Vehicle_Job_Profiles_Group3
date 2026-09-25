-- Rollback for be20_is_av_relevant_migration.sql.
BEGIN;

DROP INDEX IF EXISTS ix_jobposting_is_av_relevant;

ALTER TABLE jobposting
    DROP COLUMN IF EXISTS is_av_relevant;

COMMIT;
