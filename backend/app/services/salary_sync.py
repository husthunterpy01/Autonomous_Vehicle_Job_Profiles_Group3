"""Imports extracted salary data. Mirrors skill_sync.py/category_sync.py:
touches only the salary_* columns, nothing else on the job - safe to run
against a handoff that only carries identity + salary.
"""
from app.services.job_identity import resolve_job

SALARY_PERIODS = {"yearly", "monthly", "weekly", "daily", "hourly"}
SALARY_SOURCES = {"api", "regex", "levels_fyi_average"}


def sync_salary(db, job, row):
    if "salary_min" not in row:
        return
    salary_min = row.get("salary_min")
    salary_max = row.get("salary_max")
    salary_currency = row.get("salary_currency")
    salary_period = row.get("salary_period")
    salary_source = row.get("salary_source")

    if not isinstance(salary_min, (int, float)) or isinstance(salary_min, bool) or salary_min <= 0:
        raise ValueError("salary_min must be a positive number")
    if not isinstance(salary_max, (int, float)) or isinstance(salary_max, bool) or salary_max < salary_min:
        raise ValueError("salary_max must be a number >= salary_min")
    if not isinstance(salary_currency, str) or not salary_currency.strip():
        raise ValueError("salary_currency must be a non-empty string")
    if salary_period not in SALARY_PERIODS:
        raise ValueError(f"salary_period must be one of {sorted(SALARY_PERIODS)}")
    if salary_source not in SALARY_SOURCES:
        raise ValueError(f"salary_source must be one of {sorted(SALARY_SOURCES)}")

    job.salary_min = float(salary_min)
    job.salary_max = float(salary_max)
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
            updated += int("salary_min" in row)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Row {index + 1}: {exc}") from exc
    return {"read": len(records), "updated": updated}
