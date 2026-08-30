from __future__ import annotations

from scrapers.utils.runner import ScraperRunner


def main(argv: list[str] | None = None) -> int:
    return ScraperRunner.run(argv)


if __name__ == "__main__":
    raise SystemExit(main())
