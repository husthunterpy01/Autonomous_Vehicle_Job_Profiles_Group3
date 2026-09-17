-- Apply to an existing backend PostgreSQL database after BE-7/BE-8.
-- Repeatable and non-destructive: existing user, company, and job rows stay intact.
BEGIN;
CREATE TABLE IF NOT EXISTS favorite_job (
    user_id uuid NOT NULL REFERENCES user_account(user_id) ON DELETE CASCADE,
    job_id uuid NOT NULL REFERENCES jobposting(job_id) ON DELETE CASCADE,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, job_id)
);
CREATE INDEX IF NOT EXISTS ix_favorite_job_user_created
    ON favorite_job(user_id, created_at);
CREATE INDEX IF NOT EXISTS ix_favorite_job_job_id
    ON favorite_job(job_id);

CREATE TABLE IF NOT EXISTS favorite_company (
    user_id uuid NOT NULL REFERENCES user_account(user_id) ON DELETE CASCADE,
    company_id uuid NOT NULL REFERENCES company(company_id) ON DELETE CASCADE,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, company_id)
);
CREATE INDEX IF NOT EXISTS ix_favorite_company_user_created
    ON favorite_company(user_id, created_at);
CREATE INDEX IF NOT EXISTS ix_favorite_company_company_id
    ON favorite_company(company_id);
COMMIT;
