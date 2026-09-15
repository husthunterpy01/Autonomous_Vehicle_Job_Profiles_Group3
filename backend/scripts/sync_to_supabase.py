from __future__ import annotations

import logging
import os
import subprocess
import tempfile
from pathlib import Path
import psycopg2
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

SCHEMA = "public"

_API_ROLES = ("anon", "authenticated")


def _grant_api_read_access(target_dsn: str) -> None:
    grants = ", ".join(_API_ROLES)
    statements = (
        f"GRANT USAGE ON SCHEMA {SCHEMA} TO {grants};",
        f"GRANT SELECT ON ALL TABLES IN SCHEMA {SCHEMA} TO {grants};",
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA {SCHEMA} GRANT SELECT ON TABLES TO {grants};",
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
        subprocess.run(
            ["pg_dump", source_dsn, "--schema", SCHEMA, "--no-owner", "--no-privileges", "-Fc", "-f", str(dump_path)],
            check=True, capture_output=True, text=True,
        )
        subprocess.run(
            ["pg_restore", "-d", target_dsn, "--no-owner", "--no-privileges", "--clean", "--if-exists", str(dump_path)],
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
    except subprocess.CalledProcessError as exc:
        message = f"Supabase mirror sync failed: {(exc.stderr or str(exc)).strip()}"
        if required:
            raise RuntimeError(message) from exc
        logger.error(message)
        return False
    logger.info("Supabase mirror sync complete.")
    return True


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    load_dotenv()
    try:
        ok = sync_if_configured(required=True)
    except RuntimeError as exc:
        logger.error(str(exc))
        return 1
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
