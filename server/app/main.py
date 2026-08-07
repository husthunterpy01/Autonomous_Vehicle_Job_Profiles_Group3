from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from app.middleware.logging import setup_logging
from app.core.config import settings
from app.core.database import init_db, seed_db
from app.middleware.cors import add_cors
from app.models.company import Company
from app.models.company_location import CompanyLocation
from app.routers import api_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    seed_db()
    yield

setup_logging()
app = FastAPI(
    title=settings.app_name,
    description="API for autonomous vehicle job profiles and company data.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

add_cors(app)
app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
