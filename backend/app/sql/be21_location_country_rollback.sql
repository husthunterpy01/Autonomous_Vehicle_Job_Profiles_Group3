-- Reverts be21_location_country_migration.sql. Drops only the derived country
-- table; locations and jobs are untouched. Repeatable.
BEGIN;
DROP TABLE IF EXISTS location_country;
COMMIT;
