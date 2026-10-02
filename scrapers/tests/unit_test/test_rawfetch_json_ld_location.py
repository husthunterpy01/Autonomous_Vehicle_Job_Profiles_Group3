import json

from bs4 import BeautifulSoup
from scrapers.service.fetch.rawfetch import RawFetch


def _soup(job_posting: dict) -> BeautifulSoup:
    html = f'<html><body><script type="application/ld+json">{json.dumps(job_posting)}</script></body></html>'
    return BeautifulSoup(html, "html.parser")


def test_single_postal_address_object():
    soup = _soup({
        "@type": "JobPosting",
        "jobLocation": {
            "@type": "Place",
            "address": {
                "@type": "PostalAddress",
                "addressLocality": "San Francisco",
                "addressRegion": "CA",
                "addressCountry": "US",
            },
        },
    })
    assert RawFetch._json_ld_job_location(soup) == "San Francisco, CA, US"


def test_list_of_postal_addresses_joins_with_pipe():
    soup = _soup({
        "@type": "JobPosting",
        "jobLocation": [
            {"@type": "Place", "address": {"@type": "PostalAddress", "addressLocality": "Austin", "addressRegion": "TX"}},
            {"@type": "Place", "address": {"@type": "PostalAddress", "addressLocality": "Remote", "addressCountry": "US"}},
        ],
    })
    assert RawFetch._json_ld_job_location(soup) == "Austin, TX | Remote, US"


def test_duplicate_locations_not_repeated():
    place = {"@type": "Place", "address": {"@type": "PostalAddress", "addressLocality": "Berlin"}}
    soup = _soup({"@type": "JobPosting", "jobLocation": [place, place]})
    assert RawFetch._json_ld_job_location(soup) == "Berlin"


def test_free_text_address_string_falls_back_to_tokyo_cleanup():
    soup = _soup({
        "@type": "JobPosting",
        "jobLocation": {
            "@type": "Place",
            "address": "(Initial Assignment) 1-12-10 Kitashinagawa, Shinagawa-ku, Tokyo, and Employee's home",
        },
    })
    assert RawFetch._json_ld_job_location(soup) == "Shinagawa-ku, Tokyo"


def test_missing_jobLocation_returns_none():
    soup = _soup({"@type": "JobPosting", "title": "Example"})
    assert RawFetch._json_ld_job_location(soup) is None


def test_non_jobposting_type_ignored():
    soup = _soup({"@type": "Organization", "name": "Example"})
    assert RawFetch._json_ld_job_location(soup) is None
