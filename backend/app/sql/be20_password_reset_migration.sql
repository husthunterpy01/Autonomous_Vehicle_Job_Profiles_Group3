-- Apply to an existing backend PostgreSQL database after BE-7/BE-8.
-- Repeatable and non-destructive: existing user accounts stay intact.
BEGIN;
ALTER TABLE user_account
    ADD COLUMN IF NOT EXISTS token_version integer NOT NULL DEFAULT 0;

CREATE TABLE IF NOT EXISTS password_reset_token (
    reset_id uuid PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES user_account(user_id) ON DELETE CASCADE,
    token_hash varchar(64) NOT NULL UNIQUE,
    expires_at timestamptz NOT NULL,
    used_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_password_reset_token_user_id
    ON password_reset_token(user_id);
CREATE INDEX IF NOT EXISTS ix_password_reset_token_expires_at
    ON password_reset_token(expires_at);
COMMIT;
