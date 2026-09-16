-- Adds jobposting.employment_type_resolved: the scraped employment_type, or
-- 1 (FULL_TIME) when the source did not state one. The API serves this column;
-- employment_type keeps the raw value. Generated, so existing rows are filled
-- when the column is added and later writes cannot drift. Apply to the BACKEND
-- database after be9_migration.sql. Repeatable; does not change existing columns.
BEGIN;
ALTER TABLE jobposting ADD COLUMN IF NOT EXISTS employment_type_resolved integer
    GENERATED ALWAYS AS (COALESCE(employment_type, 1)) STORED;
COMMIT;
