from enum import Enum


class JobSortField(str, Enum):
    """Sortable columns of the job list. Salary is deliberately absent: the
    raw salary_min/salary_max columns mix pay periods, currencies and
    levels.fyi estimates, so ordering jobs by them directly is meaningless.
    (The salary_min/salary_max query params filter on an annualized,
    USD-converted figure instead - see job.list_jobs - but that conversion
    isn't exposed as a sortable, displayable value.)"""

    POSTED_DATE = "posted_date"
    TITLE = "title"
    COMPANY = "company"
