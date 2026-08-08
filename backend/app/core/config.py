import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


class Settings:
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL")
        self.app_name = os.getenv("APP_NAME", "AV Job Profiles API")
        self.api_prefix = os.getenv("API_PREFIX", "/api/v1")
        self.seed_on_startup = os.getenv("SEED_ON_STARTUP", "false").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        cors_origins = os.getenv("CORS_ORIGINS")
        if cors_origins:
            self.cors_origins = [origin.strip() for origin in cors_origins.split(",")]
        else:
            self.cors_origins = [
                "http://localhost:3000",
                "http://localhost:5173",
            ]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
