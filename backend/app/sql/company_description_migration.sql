-- Adds a short company description for the company profile page's "About" section.
-- Repeatable and safe to apply more than once.
BEGIN;

ALTER TABLE company
    ADD COLUMN IF NOT EXISTS description text;

COMMIT;
