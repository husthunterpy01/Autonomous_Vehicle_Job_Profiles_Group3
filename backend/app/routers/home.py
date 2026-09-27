from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.category import CategoryStatResponse
from app.schemas.job import TopPaidJobResponse
from app.schemas.skill import SkillStatResponse
from app.services.category_stats import CategoryService
from app.services.salary_stats import SalaryStatsService
from app.services.skill_stats import SkillService

router = APIRouter(prefix="/home", tags=["homepage"])

DbSession = Annotated[Session, Depends(get_db)]

@router.get("/skill-stats", response_model=list[SkillStatResponse])
def get_skill_stats(db: DbSession, limit: int | None = Query(default=None, gt=0)):
    skill_service = SkillService(db)
    skill_stats = skill_service.get_skill_stat_per_job(limit=limit)
    return skill_stats

@router.get("/category-stats", response_model=list[CategoryStatResponse])
def get_category_stats(db: DbSession):
    category_service = CategoryService(db)
    category_stats = category_service.get_category_stat_per_job()
    return category_stats

@router.get("/top-paid-jobs", response_model=list[TopPaidJobResponse])
def get_top_paid_jobs(db: DbSession, limit: int = Query(default=10, gt=0, le=50)):
    salary_service = SalaryStatsService(db)
    return salary_service.get_top_paid_jobs(limit=limit)
