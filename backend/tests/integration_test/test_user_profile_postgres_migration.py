"""Opt-in BE-18 migration regression in a disposable PostgreSQL schema."""

import os
from pathlib import Path
from uuid import uuid4

import psycopg2
import pytest
from psycopg2 import sql


@pytest.mark.skipif(
    os.getenv("BE18_TEST_POSTGRES") != "1",
    reason="Requires an explicitly configured PostgreSQL test database",
)
def test_user_profile_migration_is_repeatable_and_preserves_accounts():
    database_url = os.getenv("BE18_TEST_DATABASE_URL")
    if not database_url or not database_url.startswith("postgresql://"):
        pytest.fail("Set BE18_TEST_DATABASE_URL to an isolated PostgreSQL test DB")

    schema = "be18_test_" + uuid4().hex
    migration_path = (
        Path(__file__).resolve().parents[2] / "app/sql/be18_user_profile_migration.sql"
    )
    migration = migration_path.read_text(encoding="utf-8")
    connection = psycopg2.connect(database_url, connect_timeout=5)
    connection.autocommit = True
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
            cursor.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
            cursor.execute(
                "CREATE TABLE user_account "
                "(user_id uuid PRIMARY KEY, email varchar(320) NOT NULL)"
            )
            user_id = uuid4()
            cursor.execute(
                "INSERT INTO user_account (user_id, email) VALUES (%s, %s)",
                (str(user_id), "driver@example.com"),
            )

            cursor.execute(migration)
            cursor.execute(migration)

            cursor.execute(
                "SELECT column_name, character_maximum_length, is_nullable "
                "FROM information_schema.columns "
                "WHERE table_schema = %s AND table_name = 'user_account' "
                "AND column_name IN ('phone', 'address')",
                (schema,),
            )
            assert set(cursor.fetchall()) == {
                ("phone", 32, "YES"),
                ("address", 500, "YES"),
            }
            cursor.execute(
                "SELECT email, phone, address FROM user_account WHERE user_id = %s",
                (str(user_id),),
            )
            assert cursor.fetchone() == ("driver@example.com", None, None)
            cursor.execute(
                "UPDATE user_account SET phone = %s, address = %s "
                "WHERE user_id = %s",
                ("+61 412 345 678", "Perth", str(user_id)),
            )
            cursor.execute(
                "SELECT phone, address FROM user_account WHERE user_id = %s",
                (str(user_id),),
            )
            assert cursor.fetchone() == ("+61 412 345 678", "Perth")
    finally:
        with connection.cursor() as cursor:
            cursor.execute("ROLLBACK")
            cursor.execute(
                sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(
                    sql.Identifier(schema)
                )
            )
        connection.close()
