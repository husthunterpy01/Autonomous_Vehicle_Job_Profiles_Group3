import json
import os
import re
from pathlib import Path

import psycopg2
import pytest
from psycopg2.extras import RealDictCursor

from scrapers.config.postgres import PostgresConfig

JOB_POSTINGS_SQL = (
    Path(__file__).resolve().parents[2] / "dbt" / "models" / "bronze" / "job_postings.sql"
)
SOURCE_TABLE = "job_postings_test_src"


def render_job_postings_sql(source_relation: str = SOURCE_TABLE) -> str:
    sql = JOB_POSTINGS_SQL.read_text(encoding="utf-8")
    sql = re.sub(r"\{\{\s*config\([^}]*\)\s*\}\}", "", sql, count=1)
    sql = sql.replace('{{ source("bronze", "raw_responses") }}', source_relation)
    leftover = re.findall(r"\{\{.*?\}\}", sql, flags=re.DOTALL)
    if leftover:
        raise AssertionError(f"Unrendered jinja in job_postings.sql: {leftover}")
    return sql.strip()


def _connect():
    try:
        return psycopg2.connect(PostgresConfig().dsn())
    except psycopg2.OperationalError as exc:
        if os.environ.get("GITHUB_ACTIONS"):
            raise
        pytest.skip(f"Postgres is required to test job_postings.sql: {exc}")


@pytest.fixture
def pg_conn():
    connection = _connect()
    connection.autocommit = False
    try:
        yield connection
    finally:
        connection.rollback()
        connection.close()


def parse_jobs(connection, source_system, company_name, headquarter, body):
    sql = render_job_postings_sql()
    with connection.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(f"DROP TABLE IF EXISTS {SOURCE_TABLE}")
        cursor.execute(
            f"""
            CREATE TEMP TABLE {SOURCE_TABLE} (
                source text,
                source_system text,
                company_name text,
                headquarter text,
                body jsonb
            )
            """
        )
        cursor.execute(
            f"INSERT INTO {SOURCE_TABLE} VALUES (%s, %s, %s, %s, %s::jsonb)",
            ("api", source_system, company_name, headquarter, json.dumps(body)),
        )
        cursor.execute(sql)
        return [dict(row) for row in cursor.fetchall()]


def test_render_job_postings_sql_substitutes_source():
    sql = render_job_postings_sql("raw_responses")
    assert "raw_responses" in sql
    assert "{{" not in sql


def test_greenhouse_maps_jobs(pg_conn):
    jobs = parse_jobs(
        pg_conn,
        "greenhouse",
        "Stack AV",
        "US",
        {
            "jobs": [
                {
                    "title": "Engineer",
                    "content": "<p>Build autonomy software</p>",
                    "location": {"name": "Pittsburgh, PA"},
                    "first_published": "2026-01-01T00:00:00Z",
                    "absolute_url": "https://boards.greenhouse.io/stackav/jobs/1",
                }
            ]
        },
    )

    assert len(jobs) == 1
    assert jobs[0]["ats_name"] == "greenhouse"
    assert jobs[0]["company_name"] == "Stack AV"
    assert jobs[0]["job_name"] == "Engineer"
    assert jobs[0]["job_description"] == "<p>Build autonomy software</p>"
    assert jobs[0]["location"] == "Pittsburgh, PA"
    assert jobs[0]["job_url"].endswith("/jobs/1")
    assert jobs[0]["employment_type"] is None


def test_ashby_maps_jobs_and_secondary_locations(pg_conn):
    jobs = parse_jobs(
        pg_conn,
        "ashby",
        "42dot",
        "KR",
        {
            "jobs": [
                {
                    "title": "Software Engineer",
                    "descriptionPlain": "Work on autonomy.",
                    "location": "Seoul",
                    "secondaryLocations": [{"location": "Palo Alto"}],
                    "publishedAt": "2026-02-01T00:00:00Z",
                    "jobUrl": "https://jobs.ashbyhq.com/42dot/abc",
                    "employmentType": "Full-time",
                }
            ]
        },
    )

    assert jobs[0]["job_name"] == "Software Engineer"
    assert jobs[0]["location"] == "Seoul | Palo Alto"
    assert jobs[0]["employment_type"] == "Full-time"


def test_lever_maps_plain_description(pg_conn):
    jobs = parse_jobs(
        pg_conn,
        "lever",
        "Waabi",
        "CA",
        [
            {
                "text": "Research Engineer",
                "descriptionPlain": "Research autonomy.",
                "categories": {"location": "Toronto", "commitment": "Full-time"},
                "createdAt": 1700000000000,
                "hostedUrl": "https://jobs.lever.co/waabi/abc",
                "workplaceType": "hybrid",
            }
        ],
    )

    assert jobs[0]["job_name"] == "Research Engineer"
    assert jobs[0]["job_description"] == "Research autonomy."
    assert jobs[0]["location"] == "Toronto"
    assert jobs[0]["employment_type"] == "Full-time"


def test_lever_combines_body_and_lists_skipping_salary(pg_conn):
    about = (
        "PlusAI is a Physical AI company pioneering AI-based virtual driver "
        "software for factory-built autonomous trucks.\n"
    )
    jobs = parse_jobs(
        pg_conn,
        "lever",
        "Plus AI",
        "US",
        [
            {
                "text": "Principal Engineer / Director, Motion Planning",
                "openingPlain": about,
                "descriptionPlain": about,
                "descriptionBodyPlain": "",
                "lists": [
                    {
                        "text": "Responsibilities: ",
                        "content": "\n<li>Develop safety-critical software</li>\n",
                    },
                    {
                        "text": "Required Skills: ",
                        "content": "\n<li>7-10 years of experience</li>\n",
                    },
                    {
                        "text": "Salary Range",
                        "content": "\n<li>$200,000 - 280,000</li>\n",
                    },
                ],
                "categories": {"location": "Santa Clara, CA", "commitment": "Full-time"},
                "createdAt": 1728346698296,
                "hostedUrl": "https://jobs.lever.co/plus-2/4d7c4c9a",
            }
        ],
    )

    description = jobs[0]["job_description"]
    assert "Develop safety-critical software" in description
    assert "Required Skills:" in description
    assert "7-10 years of experience" in description
    assert "Salary Range" not in description
    assert "$200,000" not in description
    assert "Physical AI company" not in description


def test_lever_appends_lists_to_role_body(pg_conn):
    jobs = parse_jobs(
        pg_conn,
        "lever",
        "Plus AI",
        "US",
        [
            {
                "text": "Data Engineer (SE / Sr SE)",
                "descriptionBodyPlain": "Own driving-performance metrics at fleet scale.",
                "lists": [
                    {
                        "text": "Required Skills: ",
                        "content": "<li>Python</li>",
                    }
                ],
                "categories": {"location": "Santa Clara, CA", "commitment": "Full-time"},
                "createdAt": 1786391736074,
                "hostedUrl": "https://jobs.lever.co/plus-2/cd1e5dca",
            }
        ],
    )

    assert jobs[0]["job_description"] == (
        "Own driving-performance metrics at fleet scale.\n\n"
        "Required Skills:\n<li>Python</li>"
    )


def test_lever_maps_contract_commitment_not_workplace_type(pg_conn):
    jobs = parse_jobs(
        pg_conn,
        "lever",
        "WeRide",
        "US",
        [
            {
                "text": "Contract Vehicle Operations Specialist (Bilingual Spanish)",
                "descriptionPlain": "Operate test vehicles.",
                "categories": {
                    "location": "San Jose, CA",
                    "commitment": "Contract",
                },
                "createdAt": 1783379901263,
                "hostedUrl": "https://jobs.lever.co/weride/67194770-ca27-4291-82ac-a90e58967e29",
                "workplaceType": "onsite",
            }
        ],
    )

    assert jobs[0]["employment_type"] == "Contract"


def test_lever_employment_type_none_when_commitment_missing(pg_conn):
    jobs = parse_jobs(
        pg_conn,
        "lever",
        "Waabi",
        "CA",
        [
            {
                "text": "Engineer",
                "descriptionPlain": "Build the driver.",
                "categories": {"location": "Toronto"},
                "createdAt": 1690000000000,
                "hostedUrl": "https://jobs.lever.co/waabi/abc",
                "workplaceType": "hybrid",
            }
        ],
    )

    assert jobs[0]["employment_type"] is None


def test_smartrecruiters_maps_job_ad_sections(pg_conn):
    jobs = parse_jobs(
        pg_conn,
        "smartrecruiters",
        "Bosch",
        "DE",
        {
            "content": [
                {
                    "name": "Product Data Operator - Temporary",
                    "postingUrl": "https://jobs.smartrecruiters.com/BoschGroup/744000146470121-product-data-operator-temporary",
                    "location": {"fullLocation": "Beograd, , Serbia"},
                    "releasedDate": "2026-08-31T13:38:57.052Z",
                    "typeOfEmployment": {"label": "Full-time"},
                    "jobAd": {
                        "sections": {
                            "jobDescription": {"text": "<p>Release product documents</p>"},
                            "qualifications": {"text": "<p>SAP knowledge</p>"},
                        }
                    },
                }
            ]
        },
    )

    assert jobs[0]["job_name"] == "Product Data Operator - Temporary"
    assert jobs[0]["job_description"] == "<p>Release product documents</p>\n<p>SAP knowledge</p>"
    assert jobs[0]["job_url"].endswith("product-data-operator-temporary")
    assert jobs[0]["employment_type"] == "Full-time"


def test_smartrecruiters_employment_type_none_when_label_missing(pg_conn):
    jobs = parse_jobs(
        pg_conn,
        "smartrecruiters",
        "Bosch",
        "DE",
        {
            "content": [
                {
                    "name": "Operator",
                    "postingUrl": "https://jobs.smartrecruiters.com/BoschGroup/1",
                    "location": {"fullLocation": "Beograd, , Serbia"},
                    "releasedDate": "2026-08-31T13:38:57.052Z",
                    "jobAd": {"sections": {"jobDescription": {"text": "<p>Work</p>"}}},
                }
            ]
        },
    )

    assert jobs[0]["employment_type"] is None
