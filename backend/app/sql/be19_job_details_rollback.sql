-- Removes only schema introduced by BE-19. Dropping requirements discards data.
BEGIN;

DROP INDEX IF EXISTS ix_job_category_category_id;
DROP INDEX IF EXISTS ix_job_skill_skill_id;
DROP INDEX IF EXISTS ix_job_location_location_id;
DROP INDEX IF EXISTS ix_jobposting_salary_period;
DROP INDEX IF EXISTS ix_jobposting_posted_date;
DROP INDEX IF EXISTS ix_jobposting_employment_type;
DROP INDEX IF EXISTS ix_jobposting_company_id;
ALTER TABLE jobposting DROP COLUMN IF EXISTS requirements;

COMMIT;
