import logging
import os
import shutil
import subprocess
from dataclasses import dataclass
from urllib.parse import unquote, urlparse

from scrapers.config.postgres import PostgresConfig

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DbtConfig:
    project_dir: str = "./scrapers/dbt"
    profiles_dir: str = "./scrapers/dbt"

    def env(self, postgres_config: PostgresConfig | None = None) -> dict[str, str]:
        env = os.environ.copy()
        config = postgres_config or PostgresConfig()
        if config.dsn_override:
            parsed = urlparse(config.dsn_override)
            if parsed.hostname:
                env["POSTGRES_HOST"] = parsed.hostname
            if parsed.port:
                env["POSTGRES_PORT"] = str(parsed.port)
            if parsed.username:
                env["POSTGRES_USER"] = unquote(parsed.username)
            if parsed.password is not None:
                env["POSTGRES_PASSWORD"] = unquote(parsed.password)
            dbname = parsed.path.lstrip("/")
            if dbname:
                env["POSTGRES_DB"] = dbname
            return env
        env["POSTGRES_HOST"] = config.host
        env["POSTGRES_PORT"] = str(config.port)
        env["POSTGRES_USER"] = config.user
        env["POSTGRES_PASSWORD"] = config.password
        env["POSTGRES_DB"] = config.database
        return env

    def run(self, select: str, postgres_config: PostgresConfig | None = None) -> int:
        dbt_bin = shutil.which("dbt")
        if not dbt_bin:
            logger.error("dbt is not on PATH. Install with: pip install dbt-postgres==1.11.0")
            return 1
        completed = subprocess.run(
            [
                dbt_bin,
                "run",
                "--project-dir",
                self.project_dir,
                "--profiles-dir",
                self.profiles_dir,
                "--select",
                select,
            ],
            env=self.env(postgres_config),
        )
        if completed.returncode != 0:
            logger.error("dbt run failed with exit code %s.", completed.returncode)
            return 1
        logger.info("dbt built %s.", select)
        return 0
