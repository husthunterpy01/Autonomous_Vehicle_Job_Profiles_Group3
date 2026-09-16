from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload

from app.models import Category, Company, JobPosting, Location, Skill
from app.schemas.job import JobResponse
from app.utils.pagination import PageResponse


def to_response(job):
    return JobResponse(
        job_id=job.job_id, title=job.title, company_id=job.company_id,
        company_name=job.company.name,
        locations=sorted(location.name for location in job.locations),
        skills=sorted(skill.skill_name for skill in job.skills),
        categories=[{"category_id": c.category_id, "main_type": c.main_type, "sub_type": c.sub_type, "taxonomy_version": c.taxonomy_version}
                    for c in sorted(job.categories, key=lambda c: (c.taxonomy_version, c.normalized_name))],
        employment_type=job.employment_type_resolved, raw_description=job.raw_description,
        source_url=job.source_url, posted_date=job.posted_date,
        salary_min=job.salary_min, salary_max=job.salary_max, salary_average=job.salary_average,
        salary_currency=job.salary_currency, salary_period=job.salary_period, salary_source=job.salary_source,
    )


def job_query(db):
    return db.query(JobPosting).options(
        selectinload(JobPosting.company), selectinload(JobPosting.locations), selectinload(JobPosting.skills),
        selectinload(JobPosting.categories)
    )


def list_jobs(
    db: Session, *, q: str | None = None, location: str | None = None, skill: str | None = None,
    category_id: UUID | None = None, company_id: UUID | None = None, employment_type: int | None = None,
    min_salary: float | None = None, max_salary: float | None = None, salary_period: str | None = None,
    has_salary: bool | None = None, page: int = 1, page_size: int = 10,
):
    query = job_query(db)
    if q:
        query = query.filter(or_(JobPosting.title.icontains(q, autoescape=True), JobPosting.company.has(Company.name.icontains(q, autoescape=True))))
    if location:
        query = query.filter(JobPosting.locations.any(Location.name.icontains(location, autoescape=True)))
    if skill:
        query = query.filter(JobPosting.skills.any(Skill.skill_name.icontains(skill, autoescape=True)))
    if company_id:
        query = query.filter(JobPosting.company_id == company_id)
    if category_id:
        query = query.filter(JobPosting.categories.any(Category.category_id == category_id))
    if employment_type is not None:
        query = query.filter(JobPosting.employment_type_resolved == employment_type)
    if min_salary is not None:
        query = query.filter(JobPosting.salary_max >= min_salary)
    if max_salary is not None:
        query = query.filter(JobPosting.salary_min <= max_salary)
    if salary_period:
        query = query.filter(JobPosting.salary_period == salary_period)
    if has_salary is not None:
        # A job may only have salary_average set (a levels.fyi estimate, no
        # real disclosed range) - that still counts as "has some salary
        # info" for this flag, even though min_salary/max_salary above
        # deliberately only compare real ranges.
        condition = JobPosting.salary_min.isnot(None) | JobPosting.salary_average.isnot(None)
        query = query.filter(condition if has_salary else ~condition)
    query = query.order_by(JobPosting.posted_date.desc().nullslast(), JobPosting.job_id)
    total = query.count()
    jobs = query.offset((page - 1) * page_size).limit(page_size).all()
    return PageResponse(items=[to_response(job) for job in jobs], total=total, page=page, page_size=page_size, total_pages=(total + page_size - 1) // page_size)


def get_job(db: Session, job_id: UUID) -> JobResponse | None:
    job = job_query(db).filter(JobPosting.job_id == job_id).one_or_none()
    return to_response(job) if job is not None else None
