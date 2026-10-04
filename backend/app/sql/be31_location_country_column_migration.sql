-- BE-31: one country per location, stored on the location table itself, for the
-- exact country filter on GET /jobs?country= and GET /jobs/countries. Replaces the
-- location_country table from BE-21 (be21_location_country_migration.sql): since
-- the Silver sync splits "London; Sunnyvale" into separate locations, one place has
-- one country. A name that names no country or several ("Remote US & Canada")
-- keeps a NULL country. Apply to the BACKEND database, then fill it with
-- `python -m app.refresh_location_countries`. Repeatable.
-- Undo with be31_location_country_column_rollback.sql.
BEGIN;
ALTER TABLE location ADD COLUMN IF NOT EXISTS country text;
CREATE INDEX IF NOT EXISTS ix_location_country ON location (country);

-- Carry over what the BE-21 table already holds (only unambiguous locations),
-- then drop it. A no-op when that table was never created.
DO $$
BEGIN
    IF to_regclass('location_country') IS NOT NULL THEN
        UPDATE location
        SET country = single.country
        FROM (
            SELECT location_id, min(country) AS country
            FROM location_country
            GROUP BY location_id
            HAVING count(*) = 1
        ) AS single
        WHERE location.location_id = single.location_id;
    END IF;
END $$;
DROP TABLE IF EXISTS location_country;
COMMIT;
