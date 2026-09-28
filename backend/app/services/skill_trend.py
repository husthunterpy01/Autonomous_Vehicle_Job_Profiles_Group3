"""DOC-13: skill demand chart data from gold.skill_trend_monthly.

The view already holds one row per (month, skill) from each month-end
snapshot, with a unique rank per month, so this only picks the months and
skills to show.
"""
from sqlalchemy import Connection, func, select

from app.models.gold import skill_trend_monthly as trend
from app.schemas.trend import (
    SkillRankPointResponse,
    SkillTrendResponse,
    SkillTrendsResponse,
    TrendMonthResponse,
)


def _months_query(months: int):
    return (
        select(
            trend.c.month_key,
            trend.c.month_label,
            trend.c.snapshot_at,
            func.max(trend.c.jobs_with_skills).label("jobs_with_skills"),
        )
        .group_by(trend.c.month_key, trend.c.month_label, trend.c.snapshot_at)
        .order_by(trend.c.month_key.desc())
        .limit(months)
    )


# One month-end snapshot is at most a few hundred skills, so reading the
# shown months whole is cheaper than a per-skill query.
def _rows_query(first_month: int):
    return (
        select(
            trend.c.month_key,
            trend.c.skill_name,
            trend.c.skill_normalized_name,
            trend.c.skill_type,
            trend.c.job_count,
            trend.c.rank,
        )
        .where(trend.c.month_key >= first_month)
        .order_by(trend.c.month_key, trend.c.rank)
    )


class SkillTrendService:
    def __init__(self, connection: Connection):
        self.connection = connection

    def get_skill_trends(self, limit: int = 10, months: int = 12) -> SkillTrendsResponse:
        month_rows = self.connection.execute(_months_query(months)).mappings().all()
        if not month_rows:
            return SkillTrendsResponse(months=[], skills=[])
        month_rows = list(reversed(month_rows))  # oldest first, for the chart's x axis
        latest_month = month_rows[-1]["month_key"]

        rows = self.connection.execute(_rows_query(month_rows[0]["month_key"])).mappings().all()
        # The top skills of the latest month, in rank order.
        top = [
            (row["skill_normalized_name"], row["skill_type"])
            for row in rows
            if row["month_key"] == latest_month and row["rank"] <= limit
        ]
        skills = {key: {"name": None, "points": []} for key in top}
        for row in rows:
            skill = skills.get((row["skill_normalized_name"], row["skill_type"]))
            if skill is None:
                continue
            skill["name"] = row["skill_name"]  # rows are oldest first, so the latest display name wins
            skill["points"].append(SkillRankPointResponse(
                month_key=row["month_key"], rank=row["rank"], job_count=row["job_count"],
            ))

        return SkillTrendsResponse(
            months=[
                TrendMonthResponse(
                    month_key=row["month_key"], label=row["month_label"],
                    snapshot_at=row["snapshot_at"], jobs_with_skills=row["jobs_with_skills"],
                )
                for row in month_rows
            ],
            skills=[
                SkillTrendResponse(
                    name=skills[key]["name"], normalized_name=key[0], skill_type=key[1],
                    points=skills[key]["points"],
                )
                for key in top
            ],
        )
