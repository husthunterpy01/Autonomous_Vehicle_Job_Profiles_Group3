from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.category import CategoryStatResponse
from app.schemas.skill import (
    SkillStatResponse
)
from app.services.category_stats import CategoryService
from app.services.skill_stats import SkillService

router = APIRouter(prefix="/home", tags=["homepage"])

DbSession = Annotated[Session, Depends(get_db)]

@router.get("/skill-stats", response_model=list[SkillStatResponse])
def get_skill_stats(db: DbSession):
    skill_service = SkillService(db)
    skill_stats = skill_service.get_skill_stat_per_job()
    return skill_stats

@router.get("/category-stats", response_model=list[CategoryStatResponse])
def get_category_stats(db: DbSession):
    category_service = CategoryService(db)
    category_stats = category_service.get_category_stat_per_job()
    return category_stats