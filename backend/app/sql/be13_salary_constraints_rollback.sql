-- Reverts be13_salary_constraints_migration.sql. Removes the constraints only;
-- no data is changed. Repeatable.
BEGIN;
ALTER TABLE jobposting DROP CONSTRAINT IF EXISTS ck_jobposting_salary_min_positive;
ALTER TABLE jobposting DROP CONSTRAINT IF EXISTS ck_jobposting_salary_max_positive;
ALTER TABLE jobposting DROP CONSTRAINT IF EXISTS ck_jobposting_salary_average_positive;
ALTER TABLE jobposting DROP CONSTRAINT IF EXISTS ck_jobposting_salary_range_order;
COMMIT;
