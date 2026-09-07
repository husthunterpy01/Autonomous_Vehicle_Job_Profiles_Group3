import os
import warnings
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
        self.environment = os.getenv("ENVIRONMENT", "development").strip().lower()
        self.jwt_secret_key = os.getenv("JWT_SECRET_KEY")
        if not self.jwt_secret_key:
            if self.environment == "production":
                raise RuntimeError("JWT_SECRET_KEY is required in production")
            self.jwt_secret_key = "development-only-change-this-secret"
            warnings.warn(
                "JWT_SECRET_KEY is not set; using a development-only secret",
                stacklevel=2,
            )
        self.jwt_algorithm = "HS256"
        self.jwt_access_token_minutes = int(
            os.getenv("JWT_ACCESS_TOKEN_MINUTES", "30")
        )
        self.jwt_remember_days = int(os.getenv("JWT_REMEMBER_DAYS", "7"))
        self.auth_cookie_name = os.getenv("AUTH_COOKIE_NAME", "av_access_token")
        self.auth_cookie_secure = os.getenv(
            "AUTH_COOKIE_SECURE", "false"
        ).strip().lower() in {"1", "true", "yes", "on"}
        self.auth_login_max_attempts = int(
            os.getenv("AUTH_LOGIN_MAX_ATTEMPTS", "5")
        )
        self.auth_login_window_seconds = int(
            os.getenv("AUTH_LOGIN_WINDOW_SECONDS", "300")
        )
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
