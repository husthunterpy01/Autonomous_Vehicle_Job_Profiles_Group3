-- Reverts be22_salary_filter_index_migration.sql. Drops only the two
-- indexes; jobposting and its data are untouched. Repeatable.
BEGIN;
DROP INDEX IF EXISTS ix_jobposting_salary_min;
DROP INDEX IF EXISTS ix_jobposting_salary_max;
COMMIT;
