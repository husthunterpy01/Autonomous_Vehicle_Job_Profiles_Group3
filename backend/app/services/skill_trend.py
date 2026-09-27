"""DOC-13: skill rank chart data from gold.skill_trend_monthly.

The view already holds one row per (month, skill) from each month-end
snapshot, with a unique rank per month, so this only picks the months and
skills to show.
"""
from sqlalchemy import Connection, text

from app.schemas.trend import (
    SkillRankPointResponse,
    SkillTrendResponse,
    SkillTrendsResponse,
    TrendMonthResponse,
)

_MONTHS_SQL = text("""
    SELECT month_key, month_label, snapshot_at, max(jobs_with_skills) AS jobs_with_skills
    FROM gold.skill_trend_monthly
    GROUP BY month_key, month_label, snapshot_at
    ORDER BY month_key DESC
    LIMIT :months
""")

# One month-end snapshot is at most a few hundred skills, so reading the
# shown months whole is cheaper than a per-skill query.
_ROWS_SQL = text("""
    SELECT month_key, skill_name, skill_normalized_name, skill_type, job_count, rank
    FROM gold.skill_trend_monthly
    WHERE month_key >= :first_month
    ORDER BY month_key, rank
""")


class SkillTrendService:
    def __init__(self, connection: Connection):
        self.connection = connection

    def get_skill_trends(self, limit: int = 10, months: int = 12) -> SkillTrendsResponse:
        month_rows = self.connection.execute(_MONTHS_SQL, {"months": months}).mappings().all()
        if not month_rows:
            return SkillTrendsResponse(months=[], skills=[])
        month_rows = list(reversed(month_rows))  # oldest first, for the chart's x axis
        latest_month = month_rows[-1]["month_key"]

        rows = self.connection.execute(_ROWS_SQL, {"first_month": month_rows[0]["month_key"]}).mappings().all()
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
