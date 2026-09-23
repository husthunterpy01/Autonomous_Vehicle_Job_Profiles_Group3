"""Imports extracted salary data. Mirrors skill_sync.py/category_sync.py:
touches only the salary_* columns, nothing else on the job - safe to run
against a handoff that only carries identity + salary.
"""
from app.enums.salary_source import SalarySource
from app.schemas.job import SalaryPeriod
from app.services.job_identity import resolve_job

# Derived from SalaryPeriod (app/schemas/job.py) so the write path (here) and
# the read path (the /jobs salary_period query param) can never drift apart.
SALARY_PERIODS = {period.value for period in SalaryPeriod}
SALARY_SOURCES = {source.value for source in SalarySource}


def sync_salary(db, job, row):
    has_range = "salary_min" in row or "salary_max" in row
    has_average = "salary_average" in row
    if not has_range and not has_average:
        return
    if has_range and has_average:
        raise ValueError("salary_average and salary_min/salary_max are mutually exclusive")

    salary_currency = row.get("salary_currency")
    salary_period = row.get("salary_period")
    salary_source = row.get("salary_source")

    if not isinstance(salary_currency, str) or not salary_currency.strip():
        raise ValueError("salary_currency must be a non-empty string")
    if salary_period not in SALARY_PERIODS:
        raise ValueError(f"salary_period must be one of {sorted(SALARY_PERIODS)}")
    if salary_source not in SALARY_SOURCES:
        raise ValueError(f"salary_source must be one of {sorted(SALARY_SOURCES)}")

    if has_average:
        # A single company-wide estimate (e.g. levels_fyi_average), not a
        # real disclosed range for this posting - stored on its own column
        # rather than duplicated into salary_min/salary_max, which made an
        # estimate look like a suspiciously exact (min == max) real range
        # and let it silently dominate min_salary/max_salary comparisons
        # meant for actual disclosed ranges.
        salary_average = row.get("salary_average")
        if not isinstance(salary_average, (int, float)) or isinstance(salary_average, bool) or salary_average <= 0:
            raise ValueError("salary_average must be a positive number")
        job.salary_average = float(salary_average)
        job.salary_min = None
        job.salary_max = None
    else:
        salary_min = row.get("salary_min")
        salary_max = row.get("salary_max")
        if not isinstance(salary_min, (int, float)) or isinstance(salary_min, bool) or salary_min <= 0:
            raise ValueError("salary_min must be a positive number")
        if not isinstance(salary_max, (int, float)) or isinstance(salary_max, bool) or salary_max < salary_min:
            raise ValueError("salary_max must be a number >= salary_min")
        job.salary_min = float(salary_min)
        job.salary_max = float(salary_max)
        job.salary_average = None

    job.salary_currency = salary_currency.strip().upper()
    job.salary_period = salary_period
    job.salary_source = salary_source
    db.flush()


def import_salary(db, records):
    """Caller owns transaction and writer serialization, as for import_skills."""
    if not isinstance(records, list):
        raise TypeError("Handoff must be a JSON array")
    seen = set()
    updated = 0
    for index, row in enumerate(records):
        try:
            if not isinstance(row, dict):
                raise TypeError("Each record must be an object")
            job = resolve_job(db, row)
            if job.job_id in seen:
                raise ValueError("Multiple handoff records target the same backend job")
            seen.add(job.job_id)
            sync_salary(db, job, row)
            updated += int("salary_min" in row or "salary_average" in row)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Row {index + 1}: {exc}") from exc
    return {"read": len(records), "updated": updated}
