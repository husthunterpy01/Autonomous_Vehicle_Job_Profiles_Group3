-- Database-level salary rules, matching app/services/salary_sync.py: values are
-- positive, a range is not inverted, a job has a published range or a levels.fyi
-- estimate but never both, and any salary carries its currency, pay period and
-- source. Apply to the BACKEND database after be10_salary_migration.sql.
-- Repeatable. Fails if existing rows already break a rule - fix or remove those
-- rows first (e.g. the demo jobs from seed_companies.sql, whose salary has no
-- period or source). Undo with be13_salary_constraints_rollback.sql.
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
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'ck_jobposting_salary_range_or_average' AND conrelid = 'jobposting'::regclass
    ) THEN
        ALTER TABLE jobposting ADD CONSTRAINT ck_jobposting_salary_range_or_average
            CHECK (salary_average IS NULL OR (salary_min IS NULL AND salary_max IS NULL));
    END IF;
END $$;
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'ck_jobposting_salary_details_required' AND conrelid = 'jobposting'::regclass
    ) THEN
        ALTER TABLE jobposting ADD CONSTRAINT ck_jobposting_salary_details_required
            CHECK ((salary_min IS NULL AND salary_max IS NULL AND salary_average IS NULL)
                OR (salary_currency IS NOT NULL AND salary_period IS NOT NULL AND salary_source IS NOT NULL));
    END IF;
END $$;
COMMIT;
