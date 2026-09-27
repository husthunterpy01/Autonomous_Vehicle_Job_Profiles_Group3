"""DOC-13: copy the gold schema from the warehouse to the gold database.

dbt builds gold next to bronze and silver in the warehouse; the site reads
it from a separate PostgreSQL database (GOLD_DATABASE_URL, a Supabase
project). Gold is self-contained (no references to silver), so the whole
schema is copied and replaced in one transaction.

    python -m scrapers.service.silver_cleaning.gold_sync
"""
import logging
import os
import subprocess
import tempfile
from pathlib import Path

from scrapers.config.postgres import PostgresConfig

logger = logging.getLogger(__name__)

SCHEMA = "gold"


def sync_gold(source_dsn: str, target_dsn: str) -> None:
    with tempfile.NamedTemporaryFile(suffix=".dump", delete=False) as tmp:
        dump_path = Path(tmp.name)
    try:
        # The gold database only holds this schema, so dumping it whole
        # (including CREATE SCHEMA) is safe, unlike the backend mirror,
        # which shares Supabase's public schema with other tables.
        subprocess.run(
            # -d rather than a positional database: Windows builds of
            # pg_dump stop reading options at the first positional argument.
            ["pg_dump", "-d", source_dsn, "--schema", SCHEMA, "--no-owner", "--no-privileges", "-Fc", "-f", str(dump_path)],
            check=True, capture_output=True, text=True,
        )
        # --single-transaction: a failed restore leaves the previous copy
        # in place rather than a half-replaced schema. No Data API grants:
        # the backend reads gold over a direct connection.
        subprocess.run(
            ["pg_restore", "-d", target_dsn, "--no-owner", "--no-privileges", "--clean", "--if-exists",
             "--single-transaction", str(dump_path)],
            check=True, capture_output=True, text=True,
        )
    finally:
        dump_path.unlink(missing_ok=True)


def sync_gold_if_configured(postgres_config: PostgresConfig | None = None) -> int:
    """0 when synced or not configured (local runs without a gold database),
    1 when the copy failed."""
    target = os.environ.get("GOLD_DATABASE_URL")
    if not target:
        logger.info("GOLD_DATABASE_URL not set; skipping the gold database sync.")
        return 0
    source = (postgres_config or PostgresConfig()).dsn()
    logger.info("Copying the %s schema to the gold database...", SCHEMA)
    try:
        sync_gold(source, target)
    except (subprocess.CalledProcessError, OSError) as exc:
        # OSError covers pg_dump/pg_restore missing from PATH.
        detail = exc.stderr.strip() if isinstance(exc, subprocess.CalledProcessError) and exc.stderr else str(exc)
        logger.error("Gold database sync failed: %s", detail)
        return 1
    logger.info("Gold database sync complete.")
    return 0


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if not os.environ.get("GOLD_DATABASE_URL"):
        logger.error("Set GOLD_DATABASE_URL to the gold database's connection string.")
        return 1
    return sync_gold_if_configured()


if __name__ == "__main__":
    raise SystemExit(main())
