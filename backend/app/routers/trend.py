from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Connection

from app.core.gold_database import get_gold_connection
from app.schemas.trend import SkillTrendsResponse
from app.services.skill_trend import SkillTrendService

router = APIRouter(prefix="/trends", tags=["trends"])

GoldConnection = Annotated[Connection, Depends(get_gold_connection)]


@router.get("/skills", response_model=SkillTrendsResponse)
def get_skill_trends(
    gold: GoldConnection,
    limit: int = Query(default=10, ge=1, le=30, description="Top skills of the latest month"),
    months: int = Query(default=12, ge=1, le=36, description="Most recent months to include"),
):
    return SkillTrendService(gold).get_skill_trends(limit=limit, months=months)
