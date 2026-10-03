"""Countries named by a free-text location label (BE-21, #112).

Labels come straight from ATS payloads, so one label can name several places
("London; Sunnyvale", "Remote US & Canada") and many name only a city
("Sunnyvale", "Tel Aviv"). The result is therefore a set, and a label that
names no country at all (a bare "Remote") maps to nothing rather than a guess.
"""
import re

# Canonical country name -> lower-case names and aliases, matched on word boundaries.
_COUNTRY_NAMES = {
    "United States": [r"united states of america", r"united states", r"u\.s\.a\.?", r"u\.s\.?"],
    "United Kingdom": ["united kingdom", "england", "scotland", "great britain"],
    "Canada": ["canada"],
    "Israel": ["israel"],
    "China": ["china"],
    "Germany": ["germany", "deutschland"],
    "Hungary": ["hungary"],
    "Japan": ["japan"],
    "South Korea": ["south korea", "korea"],
    "Singapore": ["singapore"],
    "India": ["india"],
    "Taiwan": ["taiwan"],
    "Poland": ["poland"],
    "Sweden": ["sweden"],
    "Turkey": ["turkey", "türkiye", "turkiye"],
    "Portugal": ["portugal"],
    "Philippines": ["philippines"],
    "France": ["france"],
    "Netherlands": ["netherlands"],
    "Australia": ["australia"],
    "Russia": ["russia"],
    "Switzerland": ["switzerland"],
    "Spain": ["spain"],
    "Italy": ["italy"],
    "Austria": ["austria"],
    "Ireland": ["ireland"],
    "Mexico": ["mexico"],
    "Vietnam": ["vietnam", "viet nam"],
    "United Arab Emirates": ["united arab emirates", "uae"],
    "Brazil": ["brazil", "brasil"],
    "Argentina": ["argentina"],
    "Colombia": ["colombia"],
    "Uruguay": ["uruguay"],
    "Denmark": ["denmark"],
    "Finland": ["finland"],
    "Belgium": ["belgium"],
    "Ukraine": ["ukraine"],
    "Egypt": ["egypt"],
    "Hong Kong": ["hong kong"],
    "Palestine": ["palestine"],
    "Czech Republic": ["czech republic", "czechia"],
    "Romania": ["romania"],
    "Norway": ["norway"],
    "Estonia": ["estonia"],
    "Serbia": ["serbia"],
    "New Zealand": ["new zealand"],
    "Malaysia": ["malaysia"],
    "Thailand": ["thailand"],
    "Indonesia": ["indonesia"],
    "Saudi Arabia": ["saudi arabia"],
    "Qatar": ["qatar"],
}

# Upper-case only, so "us" or "uk" inside ordinary words never counts.
_COUNTRY_CODES = {"United States": ["USA", "US"], "United Kingdom": ["UK"]}

# Cities that often appear without a country. Extend when a new city-only label shows up.
_CITIES = {
    "United States": [
        "sunnyvale", "mountain view", "san francisco", "palo alto", "santa clara", "san jose",
        "foster city", "fremont", "detroit", "ann arbor", "austin", "pittsburgh", "boston", "dallas",
        "san antonio", "fort worth", "houston", "blacksburg", "novi", "pontiac", "milford", "warren",
        "phoenix", "san diego", "poway", "kirkland", "seattle", "los angeles", "las vegas", "new york",
        "allen park", "greenville", "bay area", "chicago",
    ],
    "United Kingdom": ["london", "oxford"],
    "Canada": ["toronto", "markham", "vancouver", "waterloo", "montreal"],
    "Japan": ["tokyo", "osaka", "nagoya"],
    "Israel": ["tel aviv", "jerusalem", "haifa", "ramat gan", "petah tikva", "yokneam", "herzliya"],
    "Germany": ["munich", "münchen", "stuttgart", "berlin", "ingolstadt", "böblingen", "boeblingen"],
    "Sweden": ["gothenburg", "stockholm"],
    "Poland": ["warsaw", "krakow"],
    "Hungary": ["budapest"],
    "Turkey": ["istanbul"],
    "South Korea": ["pangyo", "seoul"],
    "China": ["beijing", "shanghai", "shenzhen", "guangzhou"],
    "India": ["bengaluru", "bangalore", "pune", "hyderabad"],
    "Taiwan": ["taipei", "hsinchu"],
    "Singapore": ["one-north"],
    "Portugal": ["aveiro", "lisbon"],
    "Philippines": ["taguig", "manila"],
    "United Arab Emirates": ["dubai", "abu dhabi"],
}

_US_STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
    "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "FL": "Florida", "GA": "Georgia",
    "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts",
    "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri", "MT": "Montana",
    "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico",
    "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont",
    "VA": "Virginia", "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
    "DC": "Washington, D.C.",
}
# Georgia is also a country, so only its code (as a fallback) counts for the US state.
_US_STATE_NAMES = [re.escape(name) for code, name in _US_STATES.items() if code != "GA"] + [r"D\.C\."]
_CANADA_PROVINCES = {"ON": "Ontario", "BC": "British Columbia", "QC": "Quebec", "AB": "Alberta"}


def _words(alternatives, flags=re.IGNORECASE):
    return re.compile(r"(?<![A-Za-z])(?:" + "|".join(alternatives) + r")(?![A-Za-z])", flags)


def _escaped(words):
    return [word if "\\" in word else re.escape(word) for word in words]


_NAMED = [
    *((country, _words(_escaped(names))) for country, names in _COUNTRY_NAMES.items()),
    *((country, _words(codes, flags=0)) for country, codes in _COUNTRY_CODES.items()),
    *((country, _words(_escaped(cities))) for country, cities in _CITIES.items()),
    ("United States", _words(_US_STATE_NAMES)),
    ("Canada", _words(_escaped(_CANADA_PROVINCES.values()))),
]
# A code after a comma or space: ", CA", " CA USA", ",MI".
_CANADA_CODE = re.compile(r"[,\s]\s*(?:" + "|".join(_CANADA_PROVINCES) + r")(?![A-Za-z])")
_US_CODE = re.compile(r"[,\s]\s*(?:" + "|".join(_US_STATES) + r")(?![A-Za-z])")

KNOWN_COUNTRIES = tuple(sorted(_COUNTRY_NAMES))
_BY_LOWER = {country.lower(): country for country in KNOWN_COUNTRIES}


def _segment_countries(segment: str) -> set[str]:
    found = {country for country, pattern in _NAMED if pattern.search(segment)}
    if found:
        return found
    # Two-letter codes only when nothing else in the segment named a place:
    # ", IL", ", DE", ", IN" and ", CA" are also country codes, so
    # "Tel Aviv, IL" stays Israel and "Toronto, ON, CA" stays Canada.
    if _CANADA_CODE.search(segment):
        return {"Canada"}
    if _US_CODE.search(segment):
        return {"United States"}
    return set()


def countries_for(label: str) -> set[str]:
    """Every country the label names, one set per ';'- or '|'-separated place."""
    return set().union(*(_segment_countries(part) for part in re.split(r"[;|]", label)))


def canonical_country(value: str) -> str | None:
    """The canonical spelling of a country name, case-insensitive; None when unknown."""
    return _BY_LOWER.get(" ".join(value.split()).lower())
