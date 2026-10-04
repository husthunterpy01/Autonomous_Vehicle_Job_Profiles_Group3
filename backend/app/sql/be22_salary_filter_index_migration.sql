-- Indexes salary_min and salary_max for the job search endpoint's
-- salary_min/salary_max filter (BE-22). Names match what SQLAlchemy's
-- Column(..., index=True) would generate on a fresh database (ix_<table>_
-- <column>), so this migration and a from-scratch create_all() never
-- produce conflicting index names for the same column. Apply to the
-- BACKEND database. Repeatable. Undo with
-- be22_salary_filter_index_rollback.sql.
BEGIN;
CREATE INDEX IF NOT EXISTS ix_jobposting_salary_min ON jobposting (salary_min);
CREATE INDEX IF NOT EXISTS ix_jobposting_salary_max ON jobposting (salary_max);
COMMIT;
