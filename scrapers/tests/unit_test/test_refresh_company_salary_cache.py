import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import yaml
from scrapers.service.silver_cleaning.levels_fyi import LevelsFyiAverage
from scrapers.utils.refresh_company_salary_cache import (
    _company_names,
    _slugify,
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
