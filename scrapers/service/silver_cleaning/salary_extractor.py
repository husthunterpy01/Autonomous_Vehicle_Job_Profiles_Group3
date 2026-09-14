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
    (re.compile(r"annum|annual|\byear|\byr\b", re.IGNORECASE), "yearly"),
    (re.compile(r"\bmonth|\bmo\b", re.IGNORECASE), "monthly"),
    # "N-hour work week" describes hours per week, not pay frequency - only
    # count "week"/"weekly" as a pay period when it isn't preceded by "work".
    (re.compile(r"(?<!work )\bweek|\bwk\b", re.IGNORECASE), "weekly"),
    # "day" is not a substring of "daily" (unlike year/month/week above,
    # which are substrings of their -ly forms), so it needs its own branch.
    (re.compile(r"\bdaily\b|\bday\b", re.IGNORECASE), "daily"),
    # Same for "hour" vs "hourly". "N-hour work week" describes hours per
    # week, not an hourly pay rate - exclude bare "hour" immediately
    # followed by "work" (not "hourly", which that phrasing never precedes).
    (re.compile(r"\bhourly\b|\bhour\b(?!\s*work)|\bhr\b", re.IGNORECASE), "hourly"),
)

_SYMBOL_CLASS = "".join(re.escape(s) for s in _CURRENCY_SYMBOLS)
_NUMBER = r"[\d][\d,.]*"
_CURRENCY_TOKEN = rf"[{_SYMBOL_CLASS}]|\b(?:{'|'.join(_CURRENCY_CODES)})\b"
_RANGE_RE = re.compile(
    rf"""
    (?P<currency1>{_CURRENCY_TOKEN})?
    \s*(?P<min>{_NUMBER})
    \s*(?P<currency_after_min>{_CURRENCY_TOKEN})?
    \s*(?:-|to|–|—)\s*
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
    """Handle both US (",": thousands, ".": decimal) and European (".":
    thousands, no decimals in salary figures) grouping. A "." followed by
    exactly 3 digits (repeatable, e.g. "1.234.567") is thousands grouping,
    not a fraction - salaries are never reported to thousandths of a unit,
    and a genuine decimal (hourly cents, e.g. "25.50") always has 2 digits.
    """
    raw = raw.strip()
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", raw):
        return float(raw.replace(".", ""))
    return float(raw.replace(",", ""))


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
