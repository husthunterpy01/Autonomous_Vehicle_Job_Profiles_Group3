-- Apply to an existing backend PostgreSQL database after BE-7/BE-8.
-- Repeatable and non-destructive: existing user accounts stay intact.
BEGIN;
ALTER TABLE user_account
    ADD COLUMN IF NOT EXISTS phone varchar(32),
    ADD COLUMN IF NOT EXISTS address varchar(500);
COMMIT;
