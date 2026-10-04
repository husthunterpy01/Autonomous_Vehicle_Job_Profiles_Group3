from __future__ import annotations

import logging
import os
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

SCHEMA = "public"

_API_ROLES = ("anon", "authenticated")

_PUBLIC_TABLES = (
    "company",
    "company_location",
    "jobposting",
    "job_location",
    "job_skill",
    "job_category",
    "skill",
    "category",
    "location",
)


def _grant_api_read_access(target_dsn: str) -> None:
    import psycopg2

    grants = ", ".join(_API_ROLES)
    tables = ", ".join(f"{SCHEMA}.{table}" for table in _PUBLIC_TABLES)
    # No ALTER DEFAULT PRIVILEGES here on purpose: that would auto-grant
    # access to any *future* table too, including one that isn't safe to
    # expose - a newly added table must be added to _PUBLIC_TABLES above
    # explicitly before this script can grant access to it.
    statements = (
        f"GRANT USAGE ON SCHEMA {SCHEMA} TO {grants};",
        f"GRANT SELECT ON {tables} TO {grants};",
    )
    conn = psycopg2.connect(target_dsn)
    try:
        conn.autocommit = True
        with conn.cursor() as cursor:
            for statement in statements:
                cursor.execute(statement)
    finally:
        conn.close()


def sync_to_supabase(source_dsn: str, target_dsn: str) -> None:
    with tempfile.NamedTemporaryFile(suffix=".dump", delete=False) as tmp:
        dump_path = Path(tmp.name)
    try:
        # Explicit per-table selection (-t), not --schema + an exclude list:
        # dumping the whole schema also dumps its own CREATE SCHEMA
        # statement, which makes `pg_restore --clean` emit `DROP SCHEMA
        # public` up front - that fails once Supabase has anything else in
        # `public` that isn't part of this dump (e.g. user_account, created
        # independently there), since Postgres refuses to drop a schema out
        # from under a dependent object without CASCADE. Selecting tables
        # individually skips the schema-level statements entirely, only
        # ever touching the exact tables being mirrored - and, as a bonus,
        # this is an include-list rather than user_account being the only
        # named exclusion, so a future unrelated table added to the schema
        # doesn't leak into the mirror by default either.
        table_args = [arg for table in _PUBLIC_TABLES for arg in ("-t", f"{SCHEMA}.{table}")]
        subprocess.run(
            ["pg_dump", source_dsn, *table_args, "--no-owner", "--no-privileges", "-Fc", "-f", str(dump_path)],
            check=True, capture_output=True, text=True,
        )
        # --single-transaction: a restore that fails partway through must
        # roll back entirely rather than leave Supabase with some tables
        # updated and others stale/missing - this mirror is supposed to be
        # atomically consistent, not a table-by-table best-effort.
        subprocess.run(
            ["pg_restore", "-d", target_dsn, "--no-owner", "--no-privileges", "--clean", "--if-exists", "--single-transaction", str(dump_path)],
            check=True, capture_output=True, text=True,
        )
        try:
            _grant_api_read_access(target_dsn)
        except Exception as exc:  # noqa: BLE001 - grants are best-effort; the data mirror itself already succeeded
            logger.warning("Could not (re-)grant Data API read access after sync: %s", exc)
    finally:
        dump_path.unlink(missing_ok=True)


def sync_if_configured(*, required: bool = False) -> bool:
    """Best-effort by default: a Supabase hiccup shouldn't fail an import
    that already committed locally. Pass required=True for the standalone
    CLI, where a failure should be visible and exit non-zero.
    """
    source = os.environ.get("DATABASE_URL")
    target = os.environ.get("SUPABASE_DATABASE_URL")
    if not target:
        logger.info("SUPABASE_DATABASE_URL not set; skipping Supabase mirror sync.")
        return False
    if not source:
        logger.warning("DATABASE_URL not set; cannot mirror to Supabase.")
        return False

    logger.info("Mirroring backend public schema to Supabase...")
    try:
        sync_to_supabase(source, target)
    except (subprocess.CalledProcessError, OSError) as exc:
        # OSError (FileNotFoundError included) covers pg_dump/pg_restore not
        # being on PATH - previously only CalledProcessError was caught, so
        # a missing binary raised straight out of here and crashed whatever
        # already-committed import called this, breaking the "best-effort,
        # a Supabase hiccup shouldn't fail an import" contract this
        # function documents.
        detail = exc.stderr.strip() if isinstance(exc, subprocess.CalledProcessError) and exc.stderr else str(exc)
        message = f"Supabase mirror sync failed: {detail}"
        if required:
            raise RuntimeError(message) from exc
        logger.error(message)
        return False
    logger.info("Supabase mirror sync complete.")
    return True


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    from dotenv import load_dotenv

    load_dotenv()
    try:
        ok = sync_if_configured(required=True)
    except RuntimeError as exc:
        logger.error(str(exc))
        return 1
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
