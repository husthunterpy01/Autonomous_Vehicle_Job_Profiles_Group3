from fastapi import APIRouter

from app.routers import companies

api_router = APIRouter()
api_router.include_router(companies.router)
