-- Adds min/max/period/source alongside the existing salary_average/salary_currency
-- columns (added by be9_migration.sql). Apply to the BACKEND database before
-- running app.import_salary. Does not drop or rename any existing column.
BEGIN;
ALTER TABLE jobposting ADD COLUMN IF NOT EXISTS salary_min double precision;
ALTER TABLE jobposting ADD COLUMN IF NOT EXISTS salary_max double precision;
ALTER TABLE jobposting ADD COLUMN IF NOT EXISTS salary_period text;
ALTER TABLE jobposting ADD COLUMN IF NOT EXISTS salary_source text;
COMMIT;
