-- BE-21 (#112): the countries each location label names, for the exact country
-- filter on GET /jobs?country= and GET /jobs/countries. One label can name several
-- countries ("London; Sunnyvale"), hence a table rather than a column. Apply to the
-- BACKEND database, then fill it with `python -m app.refresh_location_countries`.
-- Repeatable. Undo with be21_location_country_rollback.sql.
BEGIN;
CREATE TABLE IF NOT EXISTS location_country (
    location_id uuid NOT NULL REFERENCES location (location_id) ON DELETE CASCADE,
    country text NOT NULL,
    PRIMARY KEY (location_id, country)
);
CREATE INDEX IF NOT EXISTS ix_location_country_country ON location_country (country);
COMMIT;
