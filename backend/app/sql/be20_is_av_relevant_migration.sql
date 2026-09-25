-- BE-20: soft-exclude non-AV-engineering jobs instead of deleting them.
-- Existing rows default to true - every row already in jobposting passed an
-- AV-relevance check before being inserted, so nothing already there changes
-- visibility. Going forward, a job later found to not be AV engineering work
-- (a corporate/ops/business function that slipped past relevance screening)
-- gets is_av_relevant set to false instead of being removed, so the decision
-- is reversible and auditable rather than destroying the row.
-- Repeatable and safe to apply after the BE-19 schema migration.
BEGIN;

ALTER TABLE jobposting
    ADD COLUMN IF NOT EXISTS is_av_relevant boolean NOT NULL DEFAULT true;

CREATE INDEX IF NOT EXISTS ix_jobposting_is_av_relevant
    ON jobposting (is_av_relevant);

COMMIT;
