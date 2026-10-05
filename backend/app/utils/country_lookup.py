"""Derive a country from a free-text job-location string (e.g. "Mountain
View, CA, USA" or "Taiwan, Hsinchu"). There is no city/country dataset in
this project, so this is a hand-rolled, rule-based lookup: every rule is a
regex over a known country/state/province/city name or abbreviation, and
when several rules match the same string (e.g. "Germany; London") the
leftmost match wins, since that is the location the posting lists first.
Returns None when no rule matches rather than guessing.
"""
from __future__ import annotations

import re

_COUNTRY_ALIASES: dict[str, str] = {
    "united states of america": "United States",
    "united states": "United States",
    "united kingdom": "United Kingdom",
    "united arab emirates": "United Arab Emirates",
    "south korea": "South Korea",
    "hong kong": "Hong Kong",
    "türkiye": "Turkey",
    "turkey": "Turkey",
    "korea": "South Korea",
    "uae": "United Arab Emirates",
    "germany": "Germany",
    "china": "China",
    "india": "India",
    "portugal": "Portugal",
    "denmark": "Denmark",
    "canada": "Canada",
    "argentina": "Argentina",
    "colombia": "Colombia",
    "brazil": "Brazil",
    "belgium": "Belgium",
    "hungary": "Hungary",
    "romania": "Romania",
    "australia": "Australia",
    "ireland": "Ireland",
    "israel": "Israel",
    "egypt": "Egypt",
    "mexico": "Mexico",
    "vietnam": "Vietnam",
    "taiwan": "Taiwan",
    "japan": "Japan",
    "netherlands": "Netherlands",
    "sweden": "Sweden",
    "poland": "Poland",
    "philippines": "Philippines",
    "singapore": "Singapore",
    "peru": "Peru",
    "uruguay": "Uruguay",
    "thailand": "Thailand",
    "switzerland": "Switzerland",
    "finland": "Finland",
    "ukraine": "Ukraine",
    "austria": "Austria",
    "italy": "Italy",
    "spain": "Spain",
    "armenia": "Armenia",
    "palestine": "Palestine",
    "france": "France",
}

# US state abbreviations are matched uppercase-only, word-boundary - two
# letters is too short to match case-insensitively without false positives.
_US_STATE_ABBREVIATIONS = ["AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC"]

# Full state names, case-insensitive. "Georgia" is deliberately excluded -
# it collides with the country of the same name, and no US-Georgia posting
# in this dataset lacks a disambiguating "GA"/"United States" token anyway.
_US_STATE_NAMES = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
    "Connecticut", "Delaware", "Florida", "Hawaii", "Idaho", "Illinois",
    "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana", "Maine",
    "Maryland", "Massachusetts", "Michigan", "Minnesota", "Mississippi",
    "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire",
    "New Jersey", "New Mexico", "New York", "North Carolina",
    "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania",
    "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas",
    "Utah", "Vermont", "Virginia", "Washington", "West Virginia",
    "Wisconsin", "Wyoming", "District of Columbia",
]

_CANADIAN_PROVINCE_ABBREVIATIONS = ["ON", "AB", "BC", "QC", "MB", "SK", "NS", "NB", "NL", "PE", "YT", "NT", "NU"]

_CANADIAN_PROVINCE_NAMES = [
    "Ontario", "Alberta", "Quebec", "British Columbia", "Manitoba",
    "Saskatchewan", "Nova Scotia", "New Brunswick", "Newfoundland",
    "Prince Edward Island", "Yukon", "Northwest Territories", "Nunavut",
]

# Bare city/facility names seen in this dataset with no accompanying
# state/country token (e.g. "Detroit", "Cruise Automation - Phoenix - ...").
_CITY_FALLBACKS: dict[str, str] = {
    "san francisco bay area": "United States",
    "san francisco": "United States",
    "phoenix": "United States",
    "sunnyvale": "United States",
    "seattle": "United States",
    "warren": "United States",
    "ann arbor": "United States",
    "austin": "United States",
    "dallas": "United States",
    "chicago": "United States",
    "houston": "United States",
    "detroit": "United States",
    "vancouver": "Canada",
    "bangalore": "India",
    "warsaw": "Poland",
    "dubai": "United Arab Emirates",
    "gothenburg": "Sweden",
    "stockholm": "Sweden",
    "london": "United Kingdom",
    "tel aviv": "Israel",
    "tokyo": "Japan",
    "seoul": "South Korea",
    "münchen": "Germany",
    "munich": "Germany",
    "böblingen": "Germany",
    "stuttgart": "Germany",
    "neunburg vorm wald": "Germany",
    "one-north": "Singapore",
}

# Named entities seen in this dataset standing in for a location rather than
# naming one, e.g. "General Motors LLC" with no city/state attached. Only
# added when the entity's own country is a verifiable fact, not a guess.
_ENTITY_FALLBACKS: dict[str, str] = {
    "general motors": "United States",
    "gm global technical center": "United States",
}


def _phrase_rules(names_to_country: dict[str, str], ignore_case: bool) -> list[tuple[re.Pattern[str], str]]:
    flags = re.IGNORECASE if ignore_case else 0
    return [
        (re.compile(r"\b" + re.escape(phrase) + r"\b", flags), country)
        for phrase, country in names_to_country.items()
    ]


def _word_rules(words: list[str], country: str, ignore_case: bool) -> list[tuple[re.Pattern[str], str]]:
    flags = re.IGNORECASE if ignore_case else 0
    return [(re.compile(r"\b" + re.escape(word) + r"\b", flags), country) for word in words]


_RULES: list[tuple[re.Pattern[str], str]] = (
    _phrase_rules(_COUNTRY_ALIASES, ignore_case=True)
    + [(re.compile(r"\bUSA\b"), "United States"), (re.compile(r"\bUS\b"), "United States")]
    + [(re.compile(r"U\.S\.A\.?\b"), "United States"), (re.compile(r"U\.S\.(?!\w)"), "United States")]
    + [(re.compile(r"\bUK\b"), "United Kingdom")]
    + _word_rules(_US_STATE_ABBREVIATIONS, "United States", ignore_case=False)
    # Observed real-world miscapitalization in scraped data (e.g. "Odessa, Tx").
    + _word_rules(["Tx"], "United States", ignore_case=False)
    + _phrase_rules({name: "United States" for name in _US_STATE_NAMES}, ignore_case=True)
    + _word_rules(_CANADIAN_PROVINCE_ABBREVIATIONS, "Canada", ignore_case=False)
    + _phrase_rules({name: "Canada" for name in _CANADIAN_PROVINCE_NAMES}, ignore_case=True)
    + _phrase_rules(_CITY_FALLBACKS, ignore_case=True)
    + _phrase_rules(_ENTITY_FALLBACKS, ignore_case=True)
)


def derive_country(raw_name: str) -> str | None:
    """Return the leftmost-matching country/state/city rule's country, or
    None if nothing in `raw_name` matches any rule."""
    best: tuple[int, str] | None = None
    for pattern, country in _RULES:
        match = pattern.search(raw_name)
        if match and (best is None or match.start() < best[0]):
            best = (match.start(), country)
    return best[1] if best else None
