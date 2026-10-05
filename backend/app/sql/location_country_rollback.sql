-- Removes only the column added by location_country_migration. country is
-- re-derivable from name via app/utils/country_lookup.py, so this is safe.
BEGIN;

ALTER TABLE location DROP COLUMN IF EXISTS country;

COMMIT;
