"""DOC-13: the gold trend mart, read-only.

Built by dbt (scrapers/dbt/models/gold) and copied to the gold database, so
it has its own MetaData: it is never part of Base.metadata, and init_db()
never creates it in the site database.
"""
from sqlalchemy import Column, DateTime, Integer, MetaData, Numeric, String, Table

gold_metadata = MetaData(schema="gold")

# View: one row per (month, skill) from each month's last completed scrape.
skill_trend_monthly = Table(
    "skill_trend_monthly",
    gold_metadata,
    Column("month_key", Integer),
    Column("month_label", String),
    Column("snapshot_at", DateTime(timezone=True)),
    Column("skill_name", String),
    Column("skill_normalized_name", String),
    Column("skill_type", String),
    Column("job_count", Integer),
    Column("jobs_with_skills", Integer),
    Column("share", Numeric),
    Column("rank", Integer),
)
