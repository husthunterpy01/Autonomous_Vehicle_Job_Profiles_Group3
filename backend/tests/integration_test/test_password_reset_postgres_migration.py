"""Opt-in BE-20 migration regression in a disposable PostgreSQL schema."""

import os
from pathlib import Path
from uuid import uuid4

import psycopg2
import pytest
from psycopg2 import sql


@pytest.mark.skipif(
    os.getenv("BE20_TEST_POSTGRES") != "1",
    reason="Requires an explicitly configured PostgreSQL test database",
)
def test_password_reset_migration_is_repeatable_and_enforces_cleanup():
    database_url = os.getenv("BE20_TEST_DATABASE_URL")
    if not database_url or not database_url.startswith("postgresql://"):
        pytest.fail("Set BE20_TEST_DATABASE_URL to an isolated PostgreSQL test DB")

    schema = "be20_test_" + uuid4().hex
    migration_path = (
        Path(__file__).resolve().parents[2]
        / "app/sql/be20_password_reset_migration.sql"
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
            cursor.execute(migration)
            cursor.execute(migration)

            cursor.execute(
                "SELECT column_name, is_nullable, column_default "
                "FROM information_schema.columns "
                "WHERE table_schema = %s AND table_name = 'user_account' "
                "AND column_name = 'token_version'",
                (schema,),
            )
            assert cursor.fetchone() == ("token_version", "NO", "0")

            user_id = uuid4()
            reset_id = uuid4()
            token_hash = "a" * 64
            cursor.execute(
                "INSERT INTO user_account (user_id) VALUES (%s)",
                (str(user_id),),
            )
            cursor.execute(
                "INSERT INTO password_reset_token "
                "(reset_id, user_id, token_hash, expires_at) "
                "VALUES (%s, %s, %s, now() + interval '20 minutes')",
                (str(reset_id), str(user_id), token_hash),
            )

            with pytest.raises(psycopg2.errors.UniqueViolation):
                cursor.execute(
                    "INSERT INTO password_reset_token "
                    "(reset_id, user_id, token_hash, expires_at) "
                    "VALUES (%s, %s, %s, now() + interval '20 minutes')",
                    (str(uuid4()), str(user_id), token_hash),
                )

            cursor.execute(
                "SELECT indexname FROM pg_indexes "
                "WHERE schemaname = %s AND tablename = 'password_reset_token'",
                (schema,),
            )
            index_names = {row[0] for row in cursor.fetchall()}
            assert "ix_password_reset_token_user_id" in index_names
            assert "ix_password_reset_token_expires_at" in index_names

            cursor.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = %s "
                "AND table_name = 'password_reset_token' "
                "AND column_name IN ('used_at', 'invalidated_at')",
                (schema,),
            )
            assert {row[0] for row in cursor.fetchall()} == {
                "invalidated_at",
                "used_at",
            }

            cursor.execute(
                "DELETE FROM user_account WHERE user_id = %s",
                (str(user_id),),
            )
            cursor.execute("SELECT count(*) FROM password_reset_token")
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
