import json
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models import Location, LocationCountry
from app.services.job import _merge_locations
from app.services.location_country import (
    assign_countries,
    country_job_counts,
    refresh_location_countries,
)
from app.services.silver_sync import SilverSync
from app.utils.location_country import KNOWN_COUNTRIES, canonical_country, countries_for


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        # Labels as they appear in the live data.
        ("Sunnyvale, California, United States of America", {"United States"}),
        ("US, CA, Santa Clara", {"United States"}),
        ("Mountain View, CA USA; San Francisco, CA USA;", {"United States"}),
        ("Pittsburgh, PA, Palo Alto, CA, Detroit, MI", {"United States"}),
        ("Remote - U.S, Ann Arbor, MI", {"United States"}),
        ("Sunnyvale", {"United States"}),
        ("London", {"United Kingdom"}),
        ("London, England, United Kingdom", {"United Kingdom"}),
        ("Toronto, ON", {"Canada"}),
        ("Pangyo (Software Dream Center), South Korea", {"South Korea"}),
        ("Istanbul, Türkiye", {"Turkey"}),
        ("One-north", {"Singapore"}),
        ("Böblingen", {"Germany"}),
        ("Location: Budapest, Hungary", {"Hungary"}),
        # One label, several countries.
        ("Remote US & Canada", {"United States", "Canada"}),
        ("London; Sunnyvale", {"United Kingdom", "United States"}),
        # Two-letter codes that are also country codes only count as a fallback.
        ("Tel Aviv, IL", {"Israel"}),
        ("Chicago, IL", {"United States"}),
        ("Toronto, ON, CA", {"Canada"}),
        ("Munich, DE", {"Germany"}),
        ("Wilmington, DE", {"United States"}),
        ("Atlanta, GA", {"United States"}),
        # Nothing to go on: no guess.
        ("Remote", set()),
        ("Georgia", set()),
        ("Latin America", set()),
        ("", set()),
    ],
)
def test_countries_for_labels(label, expected):
    assert countries_for(label) == expected


def test_canonical_country_is_case_insensitive_and_rejects_unknown_names():
    assert canonical_country(" united  STATES ") == "United States"
    assert canonical_country("south korea") == "South Korea"
    assert canonical_country("Atlantis") is None
    assert canonical_country("US") is None  # full names only, matching GET /jobs/countries
    assert list(KNOWN_COUNTRIES) == sorted(KNOWN_COUNTRIES)


def test_assign_countries_only_changes_what_differs(db_session):
    location = Location(name="London; Sunnyvale", normalized_name="london; sunnyvale")
    assert assign_countries(location) is True
    db_session.add(location)
    db_session.flush()
    assert sorted(row.country for row in location.countries) == ["United Kingdom", "United States"]
    assert assign_countries(location) is False

    location.name = "London"
    assert assign_countries(location) is True
    db_session.flush()
    assert db_session.query(LocationCountry).count() == 1
    assert location.countries[0].country == "United Kingdom"


def test_silver_sync_gives_new_locations_their_countries(db_session):
    SilverSync(db_session).run([{
        "deduplication_key": "one", "company_name": "Example AV", "job_name": "Engineer",
        "job_description": "Perception", "locations": ["Remote US & Canada", "Tel Aviv, IL", "Remote"],
    }])
    by_name = {
        location.name: sorted(row.country for row in location.countries)
        for location in db_session.query(Location).all()
    }
    assert by_name == {
        "Remote US & Canada": ["Canada", "United States"],
        "Tel Aviv, IL": ["Israel"],
        "Remote": [],
    }


def test_job_create_gives_new_locations_their_countries(db_session):
    locations = _merge_locations(db_session, [], ["Toronto, ON", "Sunnyvale"])
    assert {location.name: [row.country for row in location.countries] for location in locations} == {
        "Toronto, ON": ["Canada"],
        "Sunnyvale": ["United States"],
    }


def test_refresh_fills_missing_and_fixes_stale_countries(db_session):
    # Rows as they were before BE-21: no countries yet, or out of date.
    db_session.add_all([
        Location(name="Sunnyvale", normalized_name="sunnyvale"),
        Location(name="Remote", normalized_name="remote"),
        Location(name="London", normalized_name="london", countries=[LocationCountry(country="Canada")]),
    ])
    db_session.flush()

    assert refresh_location_countries(db_session) == {"locations": 3, "with_country": 2, "changed": 2}
    assert sorted(row.country for row in db_session.query(LocationCountry)) == ["United Kingdom", "United States"]
    assert refresh_location_countries(db_session)["changed"] == 0


def test_country_job_counts_counts_each_job_once_per_country(db_session):
    SilverSync(db_session).run([
        {"deduplication_key": "a", "company_name": "Example AV", "job_name": "A", "job_description": "x",
         "locations": ["Sunnyvale", "Mountain View, CA"]},
        {"deduplication_key": "b", "company_name": "Example AV", "job_name": "B", "job_description": "x",
         "locations": ["London; Sunnyvale"]},
        {"deduplication_key": "c", "company_name": "Example AV", "job_name": "C", "job_description": "x",
         "locations": ["Remote"]},
    ])
    assert country_job_counts(db_session) == [
        {"country": "United States", "job_count": 2},
        {"country": "United Kingdom", "job_count": 1},
    ]


def test_refresh_command_prints_the_summary(monkeypatch, capsys):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db, db.begin():
        db.add(Location(name="Tel Aviv", normalized_name="tel aviv"))

    import app.refresh_location_countries as module

    monkeypatch.setattr("sys.argv", ["command"])
    with patch.object(module, "engine", engine), patch.object(module, "sync_if_configured") as mock_sync:
        module.main()

    assert json.loads(capsys.readouterr().out) == {"locations": 1, "with_country": 1, "changed": 1}
    mock_sync.assert_called_once()
    with Session(engine) as db:
        assert [row.country for row in db.query(LocationCountry)] == ["Israel"]
