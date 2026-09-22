-- Reverts be10_salary_migration.sql by dropping the columns it added.
-- DESTRUCTIVE: every salary range, pay period and salary source is lost, and
-- constraints on those columns go with them. salary_average and salary_currency
-- existed before be10 and are kept. Back up the database first.
-- Repeatable.
BEGIN;
ALTER TABLE jobposting DROP COLUMN IF EXISTS salary_min;
ALTER TABLE jobposting DROP COLUMN IF EXISTS salary_max;
ALTER TABLE jobposting DROP COLUMN IF EXISTS salary_period;
ALTER TABLE jobposting DROP COLUMN IF EXISTS salary_source;
COMMIT;
