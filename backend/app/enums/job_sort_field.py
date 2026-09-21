from enum import Enum


class JobSortField(str, Enum):
    """Sortable columns of the job list. Salary is deliberately absent:
    values mix pay periods, currencies and levels.fyi estimates, so ordering
    them against each other is meaningless (the same reason min_salary and
    max_salary require a salary_period)."""

    POSTED_DATE = "posted_date"
    TITLE = "title"
    COMPANY = "company"
