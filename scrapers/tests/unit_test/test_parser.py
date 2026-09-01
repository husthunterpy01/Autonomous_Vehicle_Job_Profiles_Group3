from pathlib import Path

import pytest

from scrapers.utils.parser import ScraperParser


def test_parse_args_defaults():
    args = ScraperParser.parse_args([])

    assert args.company is None
    assert args.timeout == 30.0
    assert args.max_jobs == 100


def test_parse_args_accepts_company_and_limits():
    args = ScraperParser.parse_args(
        ["--company", "stack_av", "--timeout", "15", "--max-jobs", "5"]
    )

    assert args.company == "stack_av"
    assert args.timeout == 15.0
    assert args.max_jobs == 5


def test_parse_args_rejects_non_positive_timeout():
    with pytest.raises(SystemExit):
        ScraperParser.parse_args(["--timeout", "0"])


def test_parse_args_rejects_max_jobs_below_one():
    with pytest.raises(SystemExit):
        ScraperParser.parse_args(["--max-jobs", "0"])


def test_validate_common_args_rejects_non_positive_timeout():
    parser = ScraperParser.build_common_parser("test", Path("out.json"))
    args = parser.parse_args(["--timeout", "-1"])

    with pytest.raises(SystemExit):
        ScraperParser.validate_common_args(parser, args)
