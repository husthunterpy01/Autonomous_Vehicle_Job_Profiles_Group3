-- Apply to the BACKEND database before running the Silver sync.
-- Does not drop records. Repeatable for databases with the legacy ORM schema.
BEGIN;
ALTER TABLE company ALTER COLUMN company_type DROP NOT NULL;
ALTER TABLE company ALTER COLUMN website_url DROP NOT NULL;
ALTER TABLE company ALTER COLUMN career_page_url DROP NOT NULL;
ALTER TABLE jobposting ALTER COLUMN department DROP NOT NULL;
ALTER TABLE jobposting ALTER COLUMN employment_type DROP NOT NULL;
ALTER TABLE jobposting ALTER COLUMN job_location DROP NOT NULL;
ALTER TABLE jobposting ALTER COLUMN seniority_level DROP NOT NULL;
ALTER TABLE jobposting ALTER COLUMN salary_average DROP NOT NULL;
ALTER TABLE jobposting ALTER COLUMN salary_currency DROP NOT NULL;
ALTER TABLE jobposting ALTER COLUMN posted_date DROP NOT NULL;
ALTER TABLE jobposting ALTER COLUMN source_platform DROP NOT NULL;
ALTER TABLE jobposting ALTER COLUMN extraction_confidence DROP NOT NULL;
ALTER TABLE jobposting ADD COLUMN IF NOT EXISTS source_key text;
ALTER TABLE jobposting ADD COLUMN IF NOT EXISTS source_job_id text;
ALTER TABLE jobposting ADD COLUMN IF NOT EXISTS bronze_id text;
ALTER TABLE jobposting ADD COLUMN IF NOT EXISTS source_url text;
ALTER TABLE jobposting ADD COLUMN IF NOT EXISTS ingested_at timestamptz;
-- Legacy timestamps were stored without a timezone; interpret those as UTC.
DO $$ BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = current_schema() AND table_name = 'jobposting'
          AND column_name = 'posted_date' AND data_type = 'timestamp without time zone'
    ) THEN
        ALTER TABLE jobposting ALTER COLUMN posted_date TYPE timestamptz
            USING posted_date AT TIME ZONE 'UTC';
    END IF;
END $$;
CREATE UNIQUE INDEX IF NOT EXISTS uq_jobposting_source_key ON jobposting(source_key);
CREATE TABLE IF NOT EXISTS location (
    location_id uuid PRIMARY KEY,
    name text NOT NULL,
    normalized_name text NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS job_location (
    job_id uuid REFERENCES jobposting(job_id) ON DELETE CASCADE,
    location_id uuid REFERENCES location(location_id),
    PRIMARY KEY (job_id, location_id)
);
CREATE TABLE IF NOT EXISTS skill (
    skill_id uuid PRIMARY KEY,
    skill_name text NOT NULL,
    normalized_name text NOT NULL,
    skill_type varchar(64) NOT NULL,
    UNIQUE (normalized_name, skill_type)
);
CREATE TABLE IF NOT EXISTS job_skill (
    job_id uuid REFERENCES jobposting(job_id) ON DELETE CASCADE,
    skill_id uuid REFERENCES skill(skill_id),
    PRIMARY KEY (job_id, skill_id)
);
COMMIT;
