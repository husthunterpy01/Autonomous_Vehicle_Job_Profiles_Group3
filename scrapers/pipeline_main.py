from __future__ import annotations

from scrapers.utils.pipeline_runner import PipelineRunner


def main(argv: list[str] | None = None) -> int:
    return PipelineRunner.run(argv)


if __name__ == "__main__":
    raise SystemExit(main())
