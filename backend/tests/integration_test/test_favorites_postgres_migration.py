"""Opt-in BE-11 migration check in a disposable PostgreSQL schema."""

import os
from pathlib import Path
from uuid import uuid4

import psycopg2
import pytest
from psycopg2 import sql


@pytest.mark.skipif(
    os.getenv("BE11_TEST_POSTGRES") != "1",
    reason="Requires an explicitly configured PostgreSQL test database",
)
def test_favorites_migration_is_repeatable_and_enforces_cleanup():
    database_url = os.getenv("BE11_TEST_DATABASE_URL")
    if not database_url or not database_url.startswith("postgresql://"):
        pytest.fail("Set BE11_TEST_DATABASE_URL to an isolated PostgreSQL test DB")

    schema = "be11_test_" + uuid4().hex
    migration_path = (
        Path(__file__).resolve().parents[2]
        / "app/sql/be11_favorites_migration.sql"
    )
    migration = migration_path.read_text(encoding="utf-8")
    connection = psycopg2.connect(database_url, connect_timeout=5)
    connection.autocommit = True
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
            cursor.execute(
                sql.SQL("SET search_path TO {}").format(sql.Identifier(schema))
            )
            cursor.execute("CREATE TABLE user_account (user_id uuid PRIMARY KEY)")
            cursor.execute("CREATE TABLE company (company_id uuid PRIMARY KEY)")
            cursor.execute("CREATE TABLE jobposting (job_id uuid PRIMARY KEY)")
            cursor.execute(migration)
            cursor.execute(migration)

            user_id, job_id, company_id = (uuid4(), uuid4(), uuid4())
            cursor.execute("INSERT INTO user_account VALUES (%s)", (str(user_id),))
            cursor.execute("INSERT INTO company VALUES (%s)", (str(company_id),))
            cursor.execute("INSERT INTO jobposting VALUES (%s)", (str(job_id),))
            cursor.execute(
                "INSERT INTO favorite_job (user_id, job_id) VALUES (%s, %s)",
                (str(user_id), str(job_id)),
            )
            cursor.execute(
                "INSERT INTO favorite_company (user_id, company_id) "
                "VALUES (%s, %s)",
                (str(user_id), str(company_id)),
            )
            with pytest.raises(psycopg2.errors.UniqueViolation):
                cursor.execute(
                    "INSERT INTO favorite_job (user_id, job_id) VALUES (%s, %s)",
                    (str(user_id), str(job_id)),
                )

            cursor.execute(
                "SELECT indexname FROM pg_indexes "
                "WHERE schemaname = %s AND tablename IN "
                "('favorite_job', 'favorite_company')",
                (schema,),
            )
            index_names = {row[0] for row in cursor.fetchall()}
            assert "ix_favorite_job_user_created" in index_names
            assert "ix_favorite_job_job_id" in index_names
            assert "ix_favorite_company_user_created" in index_names
            assert "ix_favorite_company_company_id" in index_names

            cursor.execute("DELETE FROM jobposting WHERE job_id = %s", (str(job_id),))
            cursor.execute(
                "DELETE FROM company WHERE company_id = %s", (str(company_id),)
            )
            cursor.execute("SELECT count(*) FROM favorite_job")
            assert cursor.fetchone()[0] == 0
            cursor.execute("SELECT count(*) FROM favorite_company")
            assert cursor.fetchone()[0] == 0
    finally:
        with connection.cursor() as cursor:
            cursor.execute("ROLLBACK")
            cursor.execute(
                sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(
                    sql.Identifier(schema)
                )
            )
        connection.close()
