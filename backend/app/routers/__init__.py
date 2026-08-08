from fastapi import APIRouter

from app.routers import company

api_router = APIRouter()
api_router.include_router(company.router)
