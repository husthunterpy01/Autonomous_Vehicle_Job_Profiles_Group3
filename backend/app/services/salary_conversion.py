from sqlalchemy import case, func
from sqlalchemy.sql.elements import ColumnElement

from app.models import JobPosting

# Annualizes a period-denominated salary using a standard work year (52
# weeks x 5 days x 8 hours = 2080 hours) - a labor-statistics convention,
# not a per-company work schedule. Keys match SalaryPeriod's stored values
# exactly (app/schemas/job.py), so an unrecognized salary_period (there
# shouldn't be one - salary_sync validates against that same enum) falls
# through case()'s implicit else_=None rather than raising.
_PERIOD_TO_ANNUAL_MULTIPLIER = {
    "yearly": 1,
    "monthly": 12,
    "weekly": 52,
    "daily": 260,
    "hourly": 2080,
}

# Static, hand-set approximate USD rates - NOT pulled from a live feed, and
# not precise to the day. Set 2026-09-25 as rough spot-rate order-of-magnitude
# figures (a currency's real rate moves; these exist only to rank/compare/
# filter salaries, not to state an exact conversion). Re-check and update by
# hand periodically - there is no automatic refresh. Only the 9 currency
# codes the salary extractor ever recognizes (scrapers/service/
# silver_cleaning/salary_extractor.py's _CURRENCY_CODES) need an entry here -
# a job whose salary_currency isn't one of these (e.g. an ATS API returning a
# currency the extractor never sees) simply falls through case()'s
# else_=None and is excluded, rather than guessed at or left unconverted.
_CURRENCY_TO_USD_RATE = {
    "USD": 1.0,
    "EUR": 1.08,
    "GBP": 1.27,
    "JPY": 0.0067,
    "CAD": 0.73,
    "AUD": 0.66,
    "CHF": 1.12,
    "CNY": 0.14,
    "INR": 0.012,
}


def annual_usd_range() -> tuple[ColumnElement, ColumnElement]:
    """The disclosed range's two ends, or the levels.fyi estimate on both
    ends when there's no disclosed range (salary_sync enforces that a job
    has a range or an estimate, never both), each annualized and converted
    to USD - a common basis to rank, compare, or filter jobs on regardless
    of what currency or pay period they were actually posted in. NULL
    whenever the job has no salary at all, or its period/currency isn't one
    of the recognized keys above - there's no common basis to place it on.

    Shared by SalaryStatsService (Top Paid Jobs ranking) and job.list_jobs's
    salary_min/salary_max filter (BE-22) so both treat "what does this job
    pay, on one common scale" identically rather than diverging. """
    min_value = func.coalesce(JobPosting.salary_min, JobPosting.salary_average)
    max_value = func.coalesce(JobPosting.salary_max, JobPosting.salary_average)
    period_multiplier = case(_PERIOD_TO_ANNUAL_MULTIPLIER, value=JobPosting.salary_period)
    currency_rate = case(_CURRENCY_TO_USD_RATE, value=JobPosting.salary_currency)
    return (
        min_value * period_multiplier * currency_rate,
        max_value * period_multiplier * currency_rate,
    )
