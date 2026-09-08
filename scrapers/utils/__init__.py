from scrapers.utils.parser import ScraperParser

build_common_parser = ScraperParser.build_common_parser
validate_common_args = ScraperParser.validate_common_args
parse_args = ScraperParser.parse_args
parse_job_prefilter_args = ScraperParser.parse_job_prefilter_args

__all__ = [
    "CompanyScraper",
    "ScraperParser",
    "build_common_parser",
    "parse_args",
    "parse_job_prefilter_args",
    "validate_common_args",
]


def __getattr__(name: str):
    if name == "CompanyScraper":
        from scrapers.utils.company_scraper import CompanyScraper

        return CompanyScraper
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
