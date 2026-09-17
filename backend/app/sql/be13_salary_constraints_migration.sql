-- Database-level salary rules, matching the checks in app/services/salary_sync.py:
-- salary values are positive and a range is not inverted. Apply to the BACKEND
-- database after be10_salary_migration.sql. Repeatable. Fails if existing rows
-- already break a rule; fix those rows first rather than skipping the check.
-- Undo with be13_salary_constraints_rollback.sql.
BEGIN;
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'ck_jobposting_salary_min_positive' AND conrelid = 'jobposting'::regclass
    ) THEN
        ALTER TABLE jobposting ADD CONSTRAINT ck_jobposting_salary_min_positive
            CHECK (salary_min IS NULL OR salary_min > 0);
    END IF;
END $$;
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'ck_jobposting_salary_max_positive' AND conrelid = 'jobposting'::regclass
    ) THEN
        ALTER TABLE jobposting ADD CONSTRAINT ck_jobposting_salary_max_positive
            CHECK (salary_max IS NULL OR salary_max > 0);
    END IF;
END $$;
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'ck_jobposting_salary_average_positive' AND conrelid = 'jobposting'::regclass
    ) THEN
        ALTER TABLE jobposting ADD CONSTRAINT ck_jobposting_salary_average_positive
            CHECK (salary_average IS NULL OR salary_average > 0);
    END IF;
END $$;
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'ck_jobposting_salary_range_order' AND conrelid = 'jobposting'::regclass
    ) THEN
        ALTER TABLE jobposting ADD CONSTRAINT ck_jobposting_salary_range_order
            CHECK (salary_min IS NULL OR salary_max IS NULL OR salary_min <= salary_max);
    END IF;
END $$;
COMMIT;
