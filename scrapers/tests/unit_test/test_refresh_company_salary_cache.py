import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from urllib.error import HTTPError

import yaml
from scrapers.service.silver_cleaning.levels_fyi import LevelsFyiAverage
from scrapers.utils.refresh_company_salary_cache import (
    _company_names,
    _is_fresh,
    _slugify,
    main,
    refresh,
)


def test_slugify_lowercases_and_strips_punctuation():
    assert _slugify("Waymo") == "waymo"
    assert _slugify("Plus AI") == "plus-ai"
    assert _slugify("Aurora (formerly Aurora Innovation)") == "aurora-formerly-aurora-innovation"


def test_slugify_applies_known_overrides():
    assert _slugify("GM") == "general-motors"


def test_company_names_deduplicates_preserving_order(tmp_path):
    path = tmp_path / "av_jobs.jsonl"
    with path.open("w") as f:
        for row in [{"company_name": "Waymo"}, {"company_name": "Zoox"}, {"company_name": "Waymo"}]:
            f.write(json.dumps(row) + "\n")

    assert _company_names([path]) == ["Waymo", "Zoox"]


def test_company_names_skips_missing_input_files(tmp_path):
    present = tmp_path / "av_jobs.jsonl"
    present.write_text(json.dumps({"company_name": "Waymo"}) + "\n")
    missing = tmp_path / "does_not_exist.jsonl"

    assert _company_names([missing, present]) == ["Waymo"]


def test_is_fresh_is_false_without_a_fetched_at_timestamp():
    assert _is_fresh({}, max_age_days=30) is False


def test_is_fresh_is_false_for_an_unparseable_timestamp():
    assert _is_fresh({"fetched_at": "not-a-date"}, max_age_days=30) is False


@patch("scrapers.utils.refresh_company_salary_cache.fetch_company_average")
def test_refresh_writes_cache_entries(mock_fetch, tmp_path):
    mock_fetch.return_value = LevelsFyiAverage(330413.0, "USD", "https://www.levels.fyi/companies/waymo/salaries.md")
    cache_path = tmp_path / "company_salary.yaml"

    refresh(["Waymo"], cache_path, pause_seconds=0)

    cache = yaml.safe_load(cache_path.read_text())
    assert cache["Waymo"]["avg_total_comp"] == 330413.0
    assert cache["Waymo"]["currency"] == "USD"


@patch("scrapers.utils.refresh_company_salary_cache.fetch_company_average")
def test_refresh_skips_fresh_entries_without_force(mock_fetch, tmp_path):
    cache_path = tmp_path / "company_salary.yaml"
    cache_path.write_text(yaml.safe_dump({
        "Waymo": {
            "avg_total_comp": 100.0,
            "currency": "USD",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "levels_fyi_url": "x",
        }
    }))

    refresh(["Waymo"], cache_path, pause_seconds=0)

    mock_fetch.assert_not_called()


@patch("scrapers.utils.refresh_company_salary_cache.fetch_company_average")
def test_refresh_refetches_stale_entries(mock_fetch, tmp_path):
    mock_fetch.return_value = LevelsFyiAverage(999.0, "USD", "x")
    cache_path = tmp_path / "company_salary.yaml"
    stale = datetime.now(timezone.utc) - timedelta(days=40)
    cache_path.write_text(yaml.safe_dump({
        "Waymo": {"avg_total_comp": 100.0, "currency": "USD", "fetched_at": stale.isoformat(), "levels_fyi_url": "x"}
    }))

    refresh(["Waymo"], cache_path, max_age_days=30, pause_seconds=0)

    mock_fetch.assert_called_once()
    cache = yaml.safe_load(cache_path.read_text())
    assert cache["Waymo"]["avg_total_comp"] == 999.0


@patch("scrapers.utils.refresh_company_salary_cache.fetch_company_average")
def test_refresh_leaves_missing_companies_out_of_cache(mock_fetch, tmp_path):
    mock_fetch.return_value = None
    cache_path = tmp_path / "company_salary.yaml"

    refresh(["Unknown Co"], cache_path, pause_seconds=0)

    cache = yaml.safe_load(cache_path.read_text())
    assert cache == {}


@patch("scrapers.utils.refresh_company_salary_cache.fetch_company_average")
def test_refresh_writes_earlier_fetches_even_when_a_later_one_errors(mock_fetch, tmp_path):
    # Regression test: fetch_company_average only swallows 404s and
    # connection errors itself - a 429/403/5xx propagates as HTTPError. That
    # must not abort the whole run and lose every company already fetched
    # before it; the cache write happens once, after every company has been
    # attempted, not only on a clean run.
    def fake_fetch(slug, timeout=15.0):
        if slug == "company-b":
            raise HTTPError("url", 429, "Too Many Requests", {}, None)
        return LevelsFyiAverage(150000.0, "USD", "https://x")

    mock_fetch.side_effect = fake_fetch
    cache_path = tmp_path / "company_salary.yaml"

    result = refresh(["Company A", "Company B", "Company C"], cache_path, pause_seconds=0)

    assert set(result) == {"Company A", "Company C"}
    cache = yaml.safe_load(cache_path.read_text())
    assert set(cache) == {"Company A", "Company C"}
    assert mock_fetch.call_count == 3  # Company C is still attempted after B's error


@patch("scrapers.utils.refresh_company_salary_cache.fetch_company_average")
def test_main_reads_input_files_and_refreshes_the_cache(mock_fetch, tmp_path):
    mock_fetch.return_value = LevelsFyiAverage(200000.0, "USD", "https://x")
    input_path = tmp_path / "av_jobs.jsonl"
    input_path.write_text(json.dumps({"company_name": "Waymo"}) + "\n")
    cache_path = tmp_path / "company_salary.yaml"

    status = main(
        [
            "--input", str(input_path),
            "--cache", str(cache_path),
            "--pause-seconds", "0",
        ]
    )

    assert status == 0
    cache = yaml.safe_load(cache_path.read_text())
    assert cache["Waymo"]["avg_total_comp"] == 200000.0
    mock_fetch.assert_called_once_with("waymo")
