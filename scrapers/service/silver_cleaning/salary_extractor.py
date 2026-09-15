from __future__ import annotations

import re
from dataclasses import dataclass

from scrapers.service.llm.text import normalize_text

# Matches the shapes actually observed in scraped descriptions this session,
# e.g. "$160,000 - $262,000 per year" (Aurora/Ashby), "$135,500 - $155,000
# per year" (Greenhouse pay_input_ranges blurb text), "€50,000 - €70,000 per
# annum", "gross annual salary ... range € 50.000 - €60.000" (Bosch,
# European "." thousands separator, period stated *before* the range).
# Deliberately conservative: only a real min-max range with a recognizable
# currency and period is accepted - a single value ("up to $200,000",
# "$150,000+") is skipped rather than guessing a range, since there's no
# reliable way to turn one number into a min/max pair.
_CURRENCY_SYMBOLS = {"$": "USD", "€": "EUR", "£": "GBP", "¥": "JPY"}
_CURRENCY_CODES = frozenset({"USD", "EUR", "GBP", "JPY", "CAD", "AUD", "CHF", "CNY", "INR"})

_PERIOD_PATTERNS = (
    # A number immediately before year/month/week almost always states a
    # duration - tenure, experience, a probation period ("5+ years of
    # experience", "after 6 months") - not a pay frequency; a real pay-period
    # mention reads "per year"/"annually"/"a year" with nothing numeric
    # right before it. Excluding "<digit> year(s)" / "<digit>+ year(s)" (and
    # month/week) stops that duration text from being misread as the period.
    (re.compile(r"annum|annual|(?<!\d )(?<!\+ )\byear|\byr\b", re.IGNORECASE), "yearly"),
    (re.compile(r"(?<!\d )(?<!\+ )\bmonth|\bmo\b", re.IGNORECASE), "monthly"),
    # "N-hour work week" describes hours per week, not pay frequency - only
    # count "week"/"weekly" as a pay period when it isn't preceded by "work"
    # or a bare duration number.
    (re.compile(r"(?<!work )(?<!\d )(?<!\+ )\bweek|\bwk\b", re.IGNORECASE), "weekly"),
    # "day" is not a substring of "daily" (unlike year/month/week above,
    # which are substrings of their -ly forms), so it needs its own branch.
    (re.compile(r"\bdaily\b|\bday\b", re.IGNORECASE), "daily"),
    # Same for "hour" vs "hourly". "N-hour work week" describes hours per
    # week, not an hourly pay rate - exclude bare "hour" immediately
    # followed by "work" (not "hourly", which that phrasing never precedes).
    (re.compile(r"\bhourly\b|\bhour\b(?!\s*work)|\bhr\b", re.IGNORECASE), "hourly"),
)

# A range labeled as a bonus/relocation/stipend/referral payment is not the
# base salary and must never be returned as if it were - "Sign-on bonus of
# $5,000 - $10,000 ... Base salary $180,000 - $220,000" previously returned
# the bonus, since it's simply the first range in the text with a period
# word reachable from it (one "annual" mention early in the text can sit
# within _BEFORE_WINDOW of both ranges).
_NON_BASE_SALARY_RE = re.compile(
    r"\bbonus(es)?\b|\bsign(?:ing)?[- ]on\b|\brelocation\b|\bstipend\b|\breferral\b",
    re.IGNORECASE,
)

_SYMBOL_CLASS = "".join(re.escape(s) for s in _CURRENCY_SYMBOLS)
# Trailing k/K is shorthand for thousands ("$150K"); _parse_number scales it.
_NUMBER = r"[\d][\d,.]*[kK]?"
_CURRENCY_TOKEN = rf"[{_SYMBOL_CLASS}]|\b(?:{'|'.join(_CURRENCY_CODES)})\b"
_RANGE_RE = re.compile(
    rf"""
    (?P<currency1>{_CURRENCY_TOKEN})?
    \s*(?P<min>{_NUMBER})
    \s*(?P<currency_after_min>{_CURRENCY_TOKEN})?
    \s*(?:-|to|–|—|\band\b)\s*
    (?P<currency2>{_CURRENCY_TOKEN})?
    \s*(?P<max>{_NUMBER})
    \s*(?P<currency3>{_CURRENCY_TOKEN})?
    """,
    re.VERBOSE,
)
# How far to look for a period word ("per year", "gross annual salary ...")
# on either side of the matched number range. Asymmetric because a leading
# "gross annual salary (RAL) for this position lies within the range" style
# preamble (real example, Bosch) can run ~60 chars before the numbers,
# while a trailing period ("... per year.") is always short.
_BEFORE_WINDOW = 80
_AFTER_WINDOW = 25


@dataclass(frozen=True)
class SalaryEstimate:
    min: float
    max: float
    currency: str
    period: str


def _normalize_currency(token: str | None) -> str | None:
    if not token:
        return None
    if token in _CURRENCY_SYMBOLS:
        return _CURRENCY_SYMBOLS[token]
    upper = token.upper()
    return upper if upper in _CURRENCY_CODES else None


def _closest_period(before: str, after: str) -> str | None:
    """The period keyword textually closest to the number range wins,
    regardless of which side it's on or which category it is - a fixed
    "check yearly before hourly" priority order previously let an unrelated
    "year" earlier in the before-window (e.g. "... year in school ...")
    beat a directly-adjacent "hourly rate" that was actually describing the
    pay. Distance is measured from the number range: chars-from-the-end for
    the before-window, chars-from-the-start for the after-window.
    """
    best_distance: int | None = None
    best_period: str | None = None
    for pattern, period in _PERIOD_PATTERNS:
        for match in pattern.finditer(before):
            distance = len(before) - match.end()
            if best_distance is None or distance < best_distance:
                best_distance, best_period = distance, period
        for match in pattern.finditer(after):
            distance = match.start()
            if best_distance is None or distance < best_distance:
                best_distance, best_period = distance, period
    return best_period


def _parse_number(raw: str) -> float:
    """Handle US (",": thousands, ".": decimal), pure European (".":
    thousands, no decimal in salary figures), and full European (".":
    thousands *and* ",": decimal, e.g. "50.000,00") grouping, plus a
    trailing k/K thousands shorthand ("150K").

    A "." followed by exactly 3 digits (repeatable, e.g. "1.234.567") is
    thousands grouping, not a fraction - salaries are never reported to
    thousandths of a unit, and a genuine decimal (hourly cents, e.g.
    "25.50") always has 2 digits. The same "." thousands grouping can be
    followed by a ",XX" decimal (always 2 digits) in the full European
    format - treating that "," as a US-style thousands separator to strip
    (the previous behavior) silently collapsed "50.000,00" down to 50.0
    instead of 50000.0.
    """
    raw = raw.strip()
    thousands_shorthand = raw[-1:] in ("k", "K")
    if thousands_shorthand:
        raw = raw[:-1]
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+,\d{2}", raw):
        value = float(raw.replace(".", "").replace(",", "."))
    elif re.fullmatch(r"\d{1,3}(?:\.\d{3})+", raw):
        value = float(raw.replace(".", ""))
    else:
        value = float(raw.replace(",", ""))
    return value * 1000 if thousands_shorthand else value


def _current_clause(text: str) -> str:
    """The text since the last sentence boundary - so a "bonus" label on an
    earlier, separate sentence doesn't get attributed to a later range that
    carries its own, different label within the same before-window."""
    boundary = max(text.rfind("."), text.rfind("!"), text.rfind("?"), text.rfind(";"))
    return text[boundary + 1 :] if boundary != -1 else text


def extract_salary_from_text(description: str) -> SalaryEstimate | None:
    """Best-effort regex extraction of a base-salary range from free text.

    Returns the first match with both a resolvable currency and period -
    without either, the number pair is too ambiguous to trust (could be a
    date range, a headcount, an ID range, ...). The period is looked for in
    text on *both* sides of the number range ("per year" typically follows
    it, "gross annual salary ... range X-Y" typically precedes it).

    Normalizes the input first (strips tags, collapses HTML entities like
    "&#xa0;" down to a single space) - raw scraped descriptions can carry
    those, and left as literal 6-character sequences they blow the window
    used to look for a period word right out of range.
    """
    if not description:
        return None
    description = normalize_text(description)
    for match in _RANGE_RE.finditer(description):
        currency = _normalize_currency(
            match.group("currency1")
            or match.group("currency_after_min")
            or match.group("currency2")
            or match.group("currency3")
        )
        if currency is None:
            continue
        before = description[max(0, match.start() - _BEFORE_WINDOW):match.start()]
        after = description[match.end():match.end() + _AFTER_WINDOW]
        if _NON_BASE_SALARY_RE.search(_current_clause(before)) or _NON_BASE_SALARY_RE.search(after):
            continue
        period = _closest_period(before, after)
        if period is None:
            continue
        try:
            min_value = _parse_number(match.group("min"))
            max_value = _parse_number(match.group("max"))
        except ValueError:
            continue
        if min_value <= 0 or max_value <= min_value:
            continue
        return SalaryEstimate(min=min_value, max=max_value, currency=currency, period=period)
    return None
