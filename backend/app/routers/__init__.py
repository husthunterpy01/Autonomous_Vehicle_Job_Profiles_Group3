from fastapi import APIRouter

from app.routers import auth, company, favorite, home, job

api_router = APIRouter()
api_router.include_router(home.router)
api_router.include_router(auth.router)
api_router.include_router(company.router)
api_router.include_router(job.router)
api_router.include_router(favorite.router)

