from datetime import datetime

from pydantic import BaseModel


class TrendMonthResponse(BaseModel):
    month_key: int
    label: str
    snapshot_at: datetime
    jobs_with_skills: int


class SkillRankPointResponse(BaseModel):
    month_key: int
    rank: int
    job_count: int


class SkillTrendResponse(BaseModel):
    name: str
    normalized_name: str
    skill_type: str
    points: list[SkillRankPointResponse]


class SkillTrendsResponse(BaseModel):
    """Rank (bump) chart data: the top skills of the latest month, with
    their rank in every month shown. A month where a skill had no jobs has
    no point for it."""

    months: list[TrendMonthResponse]
    skills: list[SkillTrendResponse]
