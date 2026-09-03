import logging

from scrapers.config.dbt import DbtConfig
from scrapers.config.postgres import PostgresConfig

logger = logging.getLogger(__name__)


class SilverIngest:
    """Build the cleaned Silver model through dbt."""

    def __init__(
        self,
        postgres_config: PostgresConfig | None = None,
        dbt_config: DbtConfig | None = None,
    ) -> None:
        self.postgres_config = postgres_config or PostgresConfig()
        self.dbt_config = dbt_config or DbtConfig()

    def run(self) -> int:
        return self.dbt_config.run("+cleaned_job_postings", self.postgres_config)


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    return SilverIngest().run()


if __name__ == "__main__":
    raise SystemExit(main())
