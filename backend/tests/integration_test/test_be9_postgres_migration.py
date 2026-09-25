"""Opt-in migration check in an isolated schema; never touches public tables."""
import os
from pathlib import Path
from uuid import uuid4

import psycopg2
import pytest
from psycopg2 import sql
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.database import Base
from app.models import JobPosting
from app.services.silver_sync import SilverSync


@pytest.mark.skipif(os.getenv("BE9_TEST_POSTGRES") != "1", reason="Opt-in local PostgreSQL migration test")
def test_migration_is_repeatable_and_preserves_legacy_rows():
    root = Path(__file__).resolve().parents[3]
    database_url = os.getenv("BE9_TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not database_url or not database_url.startswith("postgresql://"):
        pytest.fail("Set BE9_TEST_DATABASE_URL to a PostgreSQL test database URL", pytrace=False)
    try:
        connection = psycopg2.connect(database_url, connect_timeout=5)
    except psycopg2.OperationalError:
        pytest.fail("Cannot connect to the PostgreSQL test database", pytrace=False)
    test_engine = None
    connection.autocommit = True
    schema = "be9_test_" + uuid4().hex
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
            cursor.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
            cursor.execute("""
                CREATE TABLE company (company_id uuid PRIMARY KEY, name text UNIQUE NOT NULL,
                    company_type text NOT NULL, website_url text NOT NULL UNIQUE,
                    career_page_url text NOT NULL UNIQUE, datasource_status text NOT NULL);
                CREATE TABLE jobposting (job_id uuid PRIMARY KEY, name text UNIQUE NOT NULL,
                    title text NOT NULL, department text NOT NULL, employment_type integer NOT NULL,
                    job_location varchar(255) NOT NULL, seniority_level integer NOT NULL, salary_average float NOT NULL,
                    salary_currency text NOT NULL, raw_description text NOT NULL, posted_date timestamp NOT NULL,
                    source_platform text NOT NULL, extraction_confidence float NOT NULL,
                    company_id uuid REFERENCES company(company_id) NOT NULL);
                INSERT INTO company VALUES ('00000000-0000-0000-0000-000000000001', 'Legacy', 'OEM',
                    'https://example.test', 'https://example.test/careers', 'confirmed');
                INSERT INTO jobposting VALUES (
                    '00000000-0000-0000-0000-000000000002', 'legacy-job', 'Legacy Engineer',
                    'Engineering', 1, 'Remote', 2, 100000, 'USD', 'Original description',
                    '2026-01-01 12:00:00', 'legacy', 0.9,
                    '00000000-0000-0000-0000-000000000001');
            """)
            migration = (root / "backend/app/sql/be9_migration.sql").read_text(encoding="utf-8")
            salary_migration = (root / "backend/app/sql/be10_salary_migration.sql").read_text(encoding="utf-8")
            cursor.execute(migration)
            cursor.execute(migration)
            cursor.execute(salary_migration)
            cursor.execute(salary_migration)
            sql_dir = root / "backend/app/sql"
            constraints_migration = (sql_dir / "be13_salary_constraints_migration.sql").read_text(encoding="utf-8")
            constraints_rollback = (sql_dir / "be13_salary_constraints_rollback.sql").read_text(encoding="utf-8")
            salary_rollback = (sql_dir / "be10_salary_migration_rollback.sql").read_text(encoding="utf-8")
            salary_constraints = "SELECT count(*) FROM pg_constraint WHERE conrelid = 'jobposting'::regclass AND conname LIKE 'ck_jobposting_salary_%'"
            salary_columns = "SELECT column_name FROM information_schema.columns WHERE table_schema = %s AND table_name = 'jobposting' AND column_name LIKE 'salary_%%' ORDER BY column_name"
            # The legacy row has salary_average but no period or source, so the
            # constraints refuse to apply until the row is fixed - and nothing is
            # left half-applied.
            with pytest.raises(psycopg2.errors.CheckViolation) as legacy:
                cursor.execute(constraints_migration)
            assert legacy.value.diag.constraint_name == "ck_jobposting_salary_details_required"
            cursor.execute("ROLLBACK")
            cursor.execute(salary_constraints)
            assert cursor.fetchone()[0] == 0
            cursor.execute("UPDATE jobposting SET salary_period = 'yearly', salary_source = 'levels_fyi_average'")
            cursor.execute(constraints_migration)
            cursor.execute(constraints_migration)
            cursor.execute(salary_constraints)
            assert cursor.fetchone()[0] == 6

            def rejected_by(statement):
                with pytest.raises(psycopg2.errors.CheckViolation) as violation:
                    cursor.execute(statement)
                return violation.value.diag.constraint_name

            assert rejected_by("UPDATE jobposting SET salary_average = 0") == "ck_jobposting_salary_average_positive"
            assert rejected_by("UPDATE jobposting SET salary_average = NULL, salary_min = 200, salary_max = 100") == "ck_jobposting_salary_range_order"
            assert rejected_by("UPDATE jobposting SET salary_min = 100, salary_max = 200") == "ck_jobposting_salary_range_or_average"
            assert rejected_by("UPDATE jobposting SET salary_period = NULL") == "ck_jobposting_salary_details_required"
            # Both rollbacks are repeatable, and the migrations re-apply cleanly after them.
            cursor.execute(constraints_rollback)
            cursor.execute(constraints_rollback)
            cursor.execute(salary_constraints)
            assert cursor.fetchone()[0] == 0
            cursor.execute(salary_rollback)
            cursor.execute(salary_rollback)
            cursor.execute(salary_columns, (schema,))
            assert cursor.fetchall() == [("salary_average",), ("salary_currency",)]
            cursor.execute(salary_migration)
            cursor.execute("UPDATE jobposting SET salary_period = 'yearly', salary_source = 'levels_fyi_average'")
            cursor.execute(constraints_migration)
            cursor.execute(salary_constraints)
            assert cursor.fetchone()[0] == 6
            cursor.execute("SELECT name FROM company")
            assert cursor.fetchall() == [("Legacy",)]
            cursor.execute("SELECT count(*) FROM job_location")
            assert cursor.fetchone()[0] == 0
            cursor.execute("SELECT count(*) FROM category")
            assert cursor.fetchone()[0] == 0
            cursor.execute("SELECT count(*) FROM job_category")
            assert cursor.fetchone()[0] == 0
            cursor.execute("SELECT count(*) FROM job_skill")
            assert cursor.fetchone()[0] == 0
            cursor.execute("SELECT title, job_location, raw_description FROM jobposting")
            assert cursor.fetchall() == [("Legacy Engineer", "Remote", "Original description")]
            cursor.execute("SELECT data_type FROM information_schema.columns WHERE table_schema = %s AND table_name = 'jobposting' AND column_name = 'job_location'", (schema,))
            assert cursor.fetchone()[0] == "text"
            drop_location_migration = (root / "backend/app/sql/be15_drop_job_location_migration.sql").read_text(encoding="utf-8")
            cursor.execute(drop_location_migration)
            cursor.execute(drop_location_migration)
            job_details_migration = (root / "backend/app/sql/be19_job_details_migration.sql").read_text(encoding="utf-8")
            cursor.execute(job_details_migration)
            cursor.execute(job_details_migration)
            av_relevant_migration = (root / "backend/app/sql/be20_is_av_relevant_migration.sql").read_text(encoding="utf-8")
            cursor.execute(av_relevant_migration)
            cursor.execute(av_relevant_migration)
            # be9 must stay repeatable once the column it used to relax is gone.
            cursor.execute(migration)
            cursor.execute("SELECT count(*) FROM information_schema.columns WHERE table_schema = %s AND table_name = 'jobposting' AND column_name = 'job_location'", (schema,))
            assert cursor.fetchone()[0] == 0
            cursor.execute("SELECT title, raw_description, requirements, is_av_relevant FROM jobposting")
            assert cursor.fetchall() == [("Legacy Engineer", "Original description", None, True)]
            cursor.execute("SELECT indexname FROM pg_indexes WHERE schemaname = %s AND indexname LIKE 'ix_job%%'", (schema,))
            index_names = {row[0] for row in cursor.fetchall()}
            assert {
                "ix_jobposting_company_id", "ix_jobposting_employment_type",
                "ix_jobposting_posted_date", "ix_jobposting_salary_period",
                "ix_job_location_location_id", "ix_job_skill_skill_id",
                "ix_job_category_category_id",
            } <= index_names
            description_migration = (root / "backend/app/sql/company_description_migration.sql").read_text(encoding="utf-8")
            cursor.execute(description_migration)
            cursor.execute(description_migration)
            cursor.execute("SELECT count(*) FROM information_schema.columns WHERE table_schema = %s AND table_name = 'company' AND column_name = 'description'", (schema,))
            assert cursor.fetchone()[0] == 1
        test_engine = create_engine(database_url, connect_args={"options": f"-csearch_path={schema}"})
        locations = [f"Office {i:02d} - Long location name" for i in range(12)]
        with Session(test_engine) as db, db.begin():
            SilverSync(db).run([{
                "deduplication_key": "f97c5d29941bfb1b2fdab0874906ab82",
                "company_name": "Legacy", "job_name": "Multi-office Engineer",
                "job_description": "Long location regression", "locations": locations,
            }])
        with Session(test_engine) as db:
            job = db.query(JobPosting).filter_by(source_key="silver:f97c5d29941bfb1b2fdab0874906ab82").one()
            assert len(job.locations) == 12
        assert "job_location" not in Base.metadata.tables["jobposting"].c
    finally:
        if test_engine is not None:
            test_engine.dispose()
        with connection.cursor() as cursor:
            cursor.execute("ROLLBACK")
            cursor.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(schema)))
        connection.close()
