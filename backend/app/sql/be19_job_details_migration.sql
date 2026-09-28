-- BE-19: full job details plus indexes used by the public filters.
-- Repeatable and safe to apply after the BE-9/BE-15 schema migrations.
BEGIN;

ALTER TABLE jobposting
    ADD COLUMN IF NOT EXISTS requirements text;

CREATE INDEX IF NOT EXISTS ix_jobposting_company_id
    ON jobposting (company_id);
CREATE INDEX IF NOT EXISTS ix_jobposting_employment_type
    ON jobposting (employment_type);
CREATE INDEX IF NOT EXISTS ix_jobposting_posted_date
    ON jobposting (posted_date);
CREATE INDEX IF NOT EXISTS ix_jobposting_salary_period
    ON jobposting (salary_period);
CREATE INDEX IF NOT EXISTS ix_job_location_location_id
    ON job_location (location_id);
CREATE INDEX IF NOT EXISTS ix_job_skill_skill_id
    ON job_skill (skill_id);
CREATE INDEX IF NOT EXISTS ix_job_category_category_id
    ON job_category (category_id);

COMMIT;
