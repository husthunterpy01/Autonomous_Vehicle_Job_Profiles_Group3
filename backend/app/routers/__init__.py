from fastapi import APIRouter

from app.routers import company, job

api_router = APIRouter()
api_router.include_router(company.router)
api_router.include_router(job.router)
