-- Adds a derived country column to location, backfilled by
-- scripts.backfill_location_country from the existing free-text name.
BEGIN;

ALTER TABLE location
    ADD COLUMN IF NOT EXISTS country text;

COMMIT;
