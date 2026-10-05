from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.enums.salary_source import SalarySource
from app.models import Company, JobPosting
from app.schemas.job import TopPaidJobResponse
from app.services.salary_conversion import annual_usd_range

# A levels.fyi estimate is company-wide, not job-specific (see
# salary_sync.py) - every job at a company with no disclosed range gets the
# identical figure. Ranking purely by value let one company with several
# estimate-only jobs fill the entire top N with duplicates of the same
# number (FE-21, reported by Weishan). Real disclosed ranges are genuinely
# per-job and stay uncapped - only estimates are capped, one per company.
_MAX_ESTIMATE_ONLY_PER_COMPANY = 1


class SalaryStatsService:
    def __init__(self, db: Session):
        self.db = db

    def get_top_paid_jobs(self, limit: int = 10) -> list[TopPaidJobResponse]:
        # NULL whenever the job has no salary at all, or its period/currency
        # isn't one of annual_usd_range()'s recognized keys - one condition
        # covers every "can't rank this" case.
        estimated_annual_usd_min, estimated_annual_usd_max = annual_usd_range()

        # Ranks each company's levels.fyi estimate-only jobs against each
        # other so the per-company cap can be applied inside SQL, before
        # LIMIT. Capping in Python after an overfetched LIMIT instead would
        # break down whenever a single company had more estimate-only jobs
        # than the overfetch window could hold: the window would fill
        # entirely with that company's duplicates before any other
        # company's rows were even fetched, so capping afterward could
        # leave far fewer than `limit` results. A real disclosed range is
        # already per-job, so its rank here is never used to filter
        # anything out.
        estimate_rank = func.row_number().over(
            partition_by=[JobPosting.company_id, JobPosting.salary_source],
            order_by=[estimated_annual_usd_max.desc(), JobPosting.job_id],
        )

        ranked = (
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
                estimate_rank.label("estimate_rank"),
            )
            .join(Company, Company.company_id == JobPosting.company_id)
            .filter(estimated_annual_usd_max.isnot(None))
            .subquery()
        )

        rows = (
            self.db.query(
                ranked.c.job_id,
                ranked.c.title,
                ranked.c.company_id,
                ranked.c.company_name,
                ranked.c.salary_min,
                ranked.c.salary_max,
                ranked.c.salary_average,
                ranked.c.salary_currency,
                ranked.c.salary_period,
                ranked.c.salary_source,
                ranked.c.estimated_annual_usd_min,
                ranked.c.estimated_annual_usd_max,
            )
            .filter(
                or_(
                    # IS DISTINCT FROM (not !=) so a row whose salary_source
                    # is somehow NULL isn't silently dropped by the cap -
                    # the cap only ever means to apply to levels_fyi_average
                    # rows specifically.
                    ranked.c.salary_source.is_distinct_from(
                        SalarySource.LEVELS_FYI_AVERAGE.value
                    ),
                    ranked.c.estimate_rank <= _MAX_ESTIMATE_ONLY_PER_COMPANY,
                )
            )
            .order_by(ranked.c.estimated_annual_usd_max.desc(), ranked.c.job_id)
            .limit(limit)
            .all()
        )

        return [TopPaidJobResponse(**row._mapping) for row in rows]
