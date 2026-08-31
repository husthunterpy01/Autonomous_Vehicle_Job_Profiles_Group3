from scrapers.utils.parser import ScraperParser
from scrapers.utils.company_scraper import CompanyScraper

build_common_parser = ScraperParser.build_common_parser
validate_common_args = ScraperParser.validate_common_args
parse_args = ScraperParser.parse_args

__all__ = [
    "CompanyScraper",
    "ScraperParser",
    "build_common_parser",
    "parse_args",
    "validate_common_args",
]
