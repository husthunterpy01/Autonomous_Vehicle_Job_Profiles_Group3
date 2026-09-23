-- Removes only the schema introduced by company_description_migration.sql.
-- Dropping description discards data.
BEGIN;

ALTER TABLE company DROP COLUMN IF EXISTS description;

COMMIT;
