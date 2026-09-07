from __future__ import annotations

import json
import logging

from scrapers.service.llm import JobPostingIO, JobPrefilter
from scrapers.utils.parser import ScraperParser


class JobPrefilterMain:
    @classmethod
    def main(cls, argv: list[str] | None = None) -> int:
        args = ScraperParser.parse_job_prefilter_args(argv)
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
        result = JobPrefilter.from_config(args.config).filter(
            JobPostingIO.load(args.input)
        )
        paths = result.write_outputs(args.output_dir)
        print(
            json.dumps(
                {
                    "before_count": result.before_count,
                    "after_count": result.after_count,
                    "excluded_count": len(result.excluded),
                    "outputs": {name: str(path) for name, path in paths.items()},
                },
                indent=2,
            )
        )
        return 0


if __name__ == "__main__":
    raise SystemExit(JobPrefilterMain.main())
