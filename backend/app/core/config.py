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
        self.environment = os.getenv("ENVIRONMENT", "").strip().lower()
        self.jwt_secret_key = os.getenv("JWT_SECRET_KEY")
        if not self.jwt_secret_key or not self.jwt_secret_key.strip():
            if self.environment != "development":
                raise RuntimeError(
                    "JWT_SECRET_KEY is required outside the development environment"
                )
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
        job_write_api_key = os.getenv("JOB_WRITE_API_KEY")
        self.job_write_api_key = (
            job_write_api_key.strip()
            if job_write_api_key and job_write_api_key.strip()
            else None
        )
        self.password_reset_token_minutes = int(
            os.getenv("PASSWORD_RESET_TOKEN_MINUTES", "20")
        )
        if not 15 <= self.password_reset_token_minutes <= 30:
            raise RuntimeError(
                "PASSWORD_RESET_TOKEN_MINUTES must be between 15 and 30"
            )
        self.password_reset_max_requests = int(
            os.getenv("PASSWORD_RESET_MAX_REQUESTS", "5")
        )
        self.password_reset_window_seconds = int(
            os.getenv("PASSWORD_RESET_WINDOW_SECONDS", "900")
        )
        self.password_reset_frontend_url = os.getenv(
            "PASSWORD_RESET_FRONTEND_URL",
            "http://localhost:3000/reset-password",
        )
        self.smtp_host = os.getenv("SMTP_HOST")
        if not self.smtp_host and self.environment != "test":
            warnings.warn(
                "SMTP_HOST is not set; password-reset emails cannot be delivered",
                stacklevel=2,
            )
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.smtp_from_email = os.getenv("SMTP_FROM_EMAIL", "no-reply@example.com")
        self.smtp_starttls = os.getenv("SMTP_STARTTLS", "true").strip().lower() in {
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
