-- Drops jobposting.job_location, the legacy free-text location label. Locations
-- live in location + job_location (the junction table), which is what the API
-- reads; nothing reads this column. Apply to the BACKEND database after
-- be9_migration.sql. Repeatable. The dropped text cannot be recovered without a
-- backup, but every location is already linked through the junction table.
BEGIN;
ALTER TABLE jobposting DROP COLUMN IF EXISTS job_location;
COMMIT;
