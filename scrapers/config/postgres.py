import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()
load_dotenv("./scrapers/.env")


@dataclass(frozen=True)
class PostgresConfig:
    host: str = os.environ.get("POSTGRES_HOST", "localhost")
    port: int = int(os.environ.get("POSTGRES_PORT", "5432"))
    database: str = os.environ.get("POSTGRES_DB", "av_jobs")
    user: str = os.environ.get("POSTGRES_USER", "av_jobs")
    password: str = os.environ.get("POSTGRES_PASSWORD", "")
    schema: str = os.environ.get("POSTGRES_SCHEMA", "bronze")
    pool_min: int = int(os.environ.get("POSTGRES_POOL_MIN", "1"))
    pool_max: int = int(os.environ.get("POSTGRES_POOL_MAX", "5"))
    dsn_override: str = os.environ.get("POSTGRES_DSN", "")

    def dsn(self) -> str:
        if self.dsn_override:
            return self.dsn_override
        return (
            f"host={self.host} port={self.port} dbname={self.database} "
            f"user={self.user} password={self.password}"
        )