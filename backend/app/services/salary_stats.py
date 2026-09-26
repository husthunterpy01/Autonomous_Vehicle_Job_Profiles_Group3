from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.models import Company, JobPosting
from app.schemas.job import TopPaidJobResponse

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
# figures (a currency's real rate moves; these exist only to rank/compare
# salaries, not to state an exact conversion). Re-check and update by hand
# periodically - there is no automatic refresh. Only the 9 currency codes the
# salary extractor ever recognizes (scrapers/service/silver_cleaning/
# salary_extractor.py's _CURRENCY_CODES) need an entry here - a job whose
# salary_currency isn't one of these (e.g. an ATS API returning a currency
# the extractor never sees) simply falls through case()'s else_=None and is
# excluded from the ranking, rather than guessed at or left unconverted.
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


class SalaryStatsService:
    def __init__(self, db: Session):
        self.db = db

    def get_top_paid_jobs(self, limit: int = 10) -> list[TopPaidJobResponse]:
        # The disclosed range's two ends, or the levels.fyi estimate on both
        # ends when there's no disclosed range (salary_sync enforces that a
        # job has a range or an estimate, never both) - so a job with only an
        # estimate reports the same min and max rather than a fabricated span.
        min_value = func.coalesce(JobPosting.salary_min, JobPosting.salary_average)
        max_value = func.coalesce(JobPosting.salary_max, JobPosting.salary_average)
        period_multiplier = case(_PERIOD_TO_ANNUAL_MULTIPLIER, value=JobPosting.salary_period)
        currency_rate = case(_CURRENCY_TO_USD_RATE, value=JobPosting.salary_currency)
        # NULL whenever the period or currency isn't one of the known keys
        # above, which also drops a job with no salary at all (min/max_value
        # NULL) - one condition covers every "can't rank this" case.
        estimated_annual_usd_min = min_value * period_multiplier * currency_rate
        estimated_annual_usd_max = max_value * period_multiplier * currency_rate

        rows = (
            self.db.query(
                JobPosting.job_id,
                JobPosting.title,
                JobPosting.company_id,
                Company.name.label("company_name"),
                JobPosting.salary_min,
                JobPosting.salary_max,
                JobPosting.salary_average,
                JobPosting.salary_currency,
                JobPosting.salary_period,
                JobPosting.salary_source,
                estimated_annual_usd_min.label("estimated_annual_usd_min"),
                estimated_annual_usd_max.label("estimated_annual_usd_max"),
            )
            .join(Company, Company.company_id == JobPosting.company_id)
            .filter(estimated_annual_usd_max.isnot(None))
            .order_by(estimated_annual_usd_max.desc(), JobPosting.job_id)
            .limit(limit)
            .all()
        )
        return [TopPaidJobResponse(**row._mapping) for row in rows]
