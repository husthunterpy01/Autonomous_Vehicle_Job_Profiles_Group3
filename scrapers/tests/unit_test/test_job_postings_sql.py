import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from scrapers.config.dbt import DbtConfig
from scrapers.config.postgres import PostgresConfig

JOB_POSTINGS_SQL = (
    Path(__file__).resolve().parents[2] / "dbt" / "models" / "bronze" / "job_postings.sql"
)
DBT_PROJECT = Path(__file__).resolve().parents[2] / "dbt"


def render_job_postings_sql(source_relation: str = "job_postings_test_src") -> str:
    sql = JOB_POSTINGS_SQL.read_text(encoding="utf-8")
    sql = re.sub(r"\{\{\s*config\([^}]*\)\s*\}\}", "", sql, count=1)
    sql = sql.replace('{{ source("bronze", "raw_responses") }}', source_relation)
    leftover = re.findall(r"\{\{.*?\}\}", sql, flags=re.DOTALL)
    if leftover:
        raise AssertionError(f"Unrendered jinja in job_postings.sql: {leftover}")
    return sql.strip()


def test_render_job_postings_sql_substitutes_source():
    sql = render_job_postings_sql("raw_responses")
    assert "raw_responses" in sql
    assert "{{" not in sql


def test_dbt_job_postings_unit_tests():
    dbt_bin = shutil.which("dbt")
    if not dbt_bin:
        if os.environ.get("GITHUB_ACTIONS"):
            pytest.fail("dbt is required to test job_postings unit tests")
        pytest.skip("dbt is required to test job_postings unit tests")

    completed = subprocess.run(
        [
            dbt_bin,
            "test",
            "--project-dir",
            str(DBT_PROJECT),
            "--profiles-dir",
            str(DBT_PROJECT),
            "--select",
            "test_type:unit",
        ],
        env=DbtConfig().env(PostgresConfig()),
        capture_output=True,
        text=True,
    )
    output = "\n".join(part for part in (completed.stdout, completed.stderr) if part)
    if completed.returncode != 0:
        if os.environ.get("GITHUB_ACTIONS"):
            pytest.fail(output)
        if "connection to server" in output or "could not connect" in output:
            pytest.skip(f"Postgres is required to test job_postings.sql: {output}")
        pytest.fail(output)
