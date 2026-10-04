-- Reverts be31_location_country_column_migration.sql: puts the BE-21 table back,
-- fills it from location.country, then drops the column. Repeatable.
BEGIN;
CREATE TABLE IF NOT EXISTS location_country (
    location_id uuid NOT NULL REFERENCES location (location_id) ON DELETE CASCADE,
    country text NOT NULL,
    PRIMARY KEY (location_id, country)
);
CREATE INDEX IF NOT EXISTS ix_location_country_country ON location_country (country);
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'location' AND column_name = 'country'
    ) THEN
        INSERT INTO location_country (location_id, country)
        SELECT location_id, country FROM location WHERE country IS NOT NULL
        ON CONFLICT DO NOTHING;
    END IF;
END $$;
DROP INDEX IF EXISTS ix_location_country;
ALTER TABLE location DROP COLUMN IF EXISTS country;
COMMIT;
