"""Opt-in migration check in an isolated schema; never touches public tables."""
import os
from pathlib import Path
from uuid import uuid4

import psycopg2
import pytest
from dotenv import dotenv_values
from psycopg2 import sql


@pytest.mark.skipif(os.getenv("BE9_TEST_POSTGRES") != "1", reason="Opt-in local PostgreSQL migration test")
def test_migration_is_repeatable_and_preserves_legacy_rows():
    root = Path(__file__).resolve().parents[3]
    config = dotenv_values(root / "scrapers" / ".env")
    connection = psycopg2.connect(
        host="127.0.0.1", port=config.get("POSTGRES_PORT", "5432"), connect_timeout=5,
        dbname=config.get("POSTGRES_DB", "av_jobs"), user=config.get("POSTGRES_USER", "av_jobs"),
        password=config.get("POSTGRES_PASSWORD", ""),
    )
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
                    job_location text NOT NULL, seniority_level integer NOT NULL, salary_average float NOT NULL,
                    salary_currency text NOT NULL, raw_description text NOT NULL, posted_date timestamp NOT NULL,
                    source_platform text NOT NULL, extraction_confidence float NOT NULL,
                    company_id uuid REFERENCES company(company_id) NOT NULL);
                INSERT INTO company VALUES ('00000000-0000-0000-0000-000000000001', 'Legacy', 'OEM',
                    'https://example.test', 'https://example.test/careers', 'confirmed');
            """)
            migration = (root / "backend/app/sql/be9_migration.sql").read_text(encoding="utf-8")
            cursor.execute(migration)
            cursor.execute(migration)
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
    finally:
        with connection.cursor() as cursor:
            cursor.execute("ROLLBACK")
            cursor.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(schema)))
        connection.close()
