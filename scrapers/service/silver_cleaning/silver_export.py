from __future__ import annotations

import argparse
import logging
from pathlib import Path

import psycopg2
import psycopg2.extras
from scrapers.config.postgres import PostgresConfig
from scrapers.service.llm.io import JobPostingIO

logger = logging.getLogger(__name__)

SELECT_SQL = "SELECT * FROM silver.cleaned_job_postings ORDER BY deduplication_key"
DEFAULT_OUTPUT_PATH = Path("data") / "silver_export.jsonl"


class SilverExport:
    """Pulls the dbt-built Silver staging table out to a JSONL file.

    The AV prefilter/classify/enrich stages are file-based (they predate any
    direct Postgres wiring - see backend/SILVER_SYNC.md), so this is the
    handoff point between the dbt-managed `silver.cleaned_job_postings` table
    and the rest of the LLM categorization pipeline.
    """

    def __init__(self, postgres_config: PostgresConfig | None = None) -> None:
        self.postgres_config = postgres_config or PostgresConfig()

    def export(self, output_path: str | Path) -> int:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        connection = psycopg2.connect(self.postgres_config.dsn())
        try:
            with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(SELECT_SQL)
                rows = [dict(row) for row in cursor]
        finally:
            connection.close()

        JobPostingIO.write_json_lines(output_path, rows)
        logger.info("Exported %d Silver rows to %s.", len(rows), output_path)
        return len(rows)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    parser = argparse.ArgumentParser(
        description="Export silver.cleaned_job_postings to a JSONL file."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=f"JSONL output path (default: {DEFAULT_OUTPUT_PATH})",
    )
    args = parser.parse_args(argv)
    SilverExport().export(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
