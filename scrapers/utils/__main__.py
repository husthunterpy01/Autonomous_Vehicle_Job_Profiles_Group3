from __future__ import annotations

from scrapers.utils.runner import ScraperRunner


class ScraperMain:
    @classmethod
    def main(cls, argv: list[str] | None = None) -> int:
        return ScraperRunner.run(argv)


if __name__ == "__main__":
    raise SystemExit(ScraperMain.main())
