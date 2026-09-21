import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.enums.job_sort_field import JobSortField
from app.enums.sort_direction import SortDirection
from app.models import Category, Company, JobPosting, Location, Skill
from app.schemas.job import CategoryResponse, JobCreate, JobDetailResponse, JobResponse
from app.services.category_sync import dominant_categories
from app.utils.pagination import PageResponse

logger = logging.getLogger(__name__)


def _to_category_response(categories) -> CategoryResponse | None:
    """Shapes a job's Category rows into the response's one-main-type-with-
    its-sub_types contract. sync_categories now enforces that invariant at
    write time (see category_sync.dominant_categories), but this still
    collapses to the dominant group defensively for any job written before
    that enforcement existed, rather than misreporting a mixed job as
    single-main_type-clean.
    """
    if not categories:
        return None
    members = dominant_categories(categories)
    if not members:
        return None
    return CategoryResponse(
        main_type=members[0].main_type,
        taxonomy_version=members[0].taxonomy_version,
        sub_types=[
            {"category_id": c.category_id, "sub_type": c.sub_type} for c in members
        ],
    )


def to_response(job):
    return JobResponse(
        job_id=job.job_id,
        title=job.title,
        company_id=job.company_id,
        company_name=job.company.name,
        locations=sorted(location.name for location in job.locations),
        skills=sorted(skill.skill_name for skill in job.skills),
        category=_to_category_response(job.categories),
        employment_type=job.employment_type,
        raw_description=job.raw_description,
        source_url=job.source_url,
        posted_date=job.posted_date,
        salary_min=job.salary_min,
        salary_max=job.salary_max,
        salary_average=job.salary_average,
        salary_currency=job.salary_currency,
        salary_period=job.salary_period,
        salary_source=job.salary_source,
    )


def to_detail_response(job) -> JobDetailResponse:
    return JobDetailResponse(
        **to_response(job).model_dump(),
        department=job.department,
        seniority_level=job.seniority_level,
        requirements=job.requirements,
        source_platform=job.source_platform,
        source_job_id=job.source_job_id,
    )


def job_query(db):
    return db.query(JobPosting).options(
        selectinload(JobPosting.company),
        selectinload(JobPosting.locations),
        selectinload(JobPosting.skills),
        selectinload(JobPosting.categories),
    )


# Newest first reads best for dates; A-Z for names. Each entry is the
# default direction plus the column to order by. Company is sorted by the
# company name rather than its UUID, so the join below is required.
_SORT_COLUMNS = {
    JobSortField.POSTED_DATE: (SortDirection.DESC, JobPosting.posted_date),
    JobSortField.TITLE: (SortDirection.ASC, func.lower(JobPosting.title)),
    JobSortField.COMPANY: (SortDirection.ASC, func.lower(Company.name)),
}


def _apply_sort(query, sort: JobSortField, direction: SortDirection | None):
    default_direction, column = _SORT_COLUMNS[sort]
    if sort is JobSortField.COMPANY:
        # LEFT JOIN, not an inner join: company_id is NOT NULL today, but if
        # that ever changed a job without a company should sort last like any
        # other missing value instead of silently dropping out of the list.
        # Many-to-one either way, so this cannot duplicate job rows.
        query = query.outerjoin(Company, JobPosting.company_id == Company.company_id)
    ordering = column.desc() if (direction or default_direction) is SortDirection.DESC else column.asc()
    # Jobs missing the sorted value go last whichever direction is chosen,
    # so an empty column never occupies the first page. job_id breaks ties
    # so a row cannot drift between pages while paginating.
    return query.order_by(ordering.nullslast(), JobPosting.job_id)


def list_jobs(
    db: Session,
    *,
    q: str | None = None,
    location: str | None = None,
    skill: str | None = None,
    category_id: UUID | None = None,
    company_id: UUID | None = None,
    employment_type: int | None = None,
    min_salary: float | None = None,
    max_salary: float | None = None,
    salary_period: str | None = None,
    has_salary: bool | None = None,
    sort: JobSortField = JobSortField.POSTED_DATE,
    direction: SortDirection | None = None,
    page: int = 1,
    page_size: int = 10,
):
    query = job_query(db)
    if q:
        query = query.filter(
            or_(
                JobPosting.title.icontains(q, autoescape=True),
                JobPosting.company.has(Company.name.icontains(q, autoescape=True)),
            )
        )
    if location:
        query = query.filter(
            JobPosting.locations.any(Location.name.icontains(location, autoescape=True))
        )
    if skill:
        query = query.filter(
            JobPosting.skills.any(Skill.skill_name.icontains(skill, autoescape=True))
        )
    if company_id:
        query = query.filter(JobPosting.company_id == company_id)
    if category_id:
        query = query.filter(
            JobPosting.categories.any(Category.category_id == category_id)
        )
    if employment_type is not None:
        query = query.filter(JobPosting.employment_type == employment_type)
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
        condition = JobPosting.salary_min.isnot(None) | JobPosting.salary_average.isnot(
            None
        )
        query = query.filter(condition if has_salary else ~condition)
    query = _apply_sort(query, sort, direction)
    total = query.count()
    jobs = query.offset((page - 1) * page_size).limit(page_size).all()
    return PageResponse(
        items=[to_response(job) for job in jobs],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


def get_job(db: Session, job_id: UUID) -> JobDetailResponse | None:
    job = job_query(db).filter(JobPosting.job_id == job_id).one_or_none()
    return to_detail_response(job) if job is not None else None


def _load_related(db: Session, model, id_column, ids: list[UUID], label: str):
    if not ids:
        return []
    rows = db.query(model).filter(id_column.in_(ids)).all()
    found = {getattr(row, id_column.key) for row in rows}
    missing = [str(item_id) for item_id in ids if item_id not in found]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown {label} IDs: {', '.join(missing)}",
        )
    return rows


def _is_unique_violation(exc: IntegrityError) -> bool:
    original = getattr(exc, "orig", None)
    sqlstate = getattr(original, "sqlstate", None) or getattr(original, "pgcode", None)
    return sqlstate == "23505" or "unique constraint" in str(original).lower()


def create_job(db: Session, data: JobCreate) -> JobDetailResponse:
    """Create one system-supplied job and link existing taxonomy entities.

    The caller provides a stable source_key. Prefixing it keeps this write
    channel's namespace separate from keys produced by the Silver importer.
    """
    storage_key = f"api:{data.source_key}"
    try:
        if db.get(Company, data.company_id) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company not found: {data.company_id}",
            )
        if (
            db.query(JobPosting).filter(JobPosting.source_key == storage_key).first()
            is not None
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Job already exists for source_key: {data.source_key}",
            )

        locations = _load_related(
            db, Location, Location.location_id, data.location_ids, "location"
        )
        skills = _load_related(db, Skill, Skill.skill_id, data.skill_ids, "skill")
        categories = _load_related(
            db, Category, Category.category_id, data.category_ids, "category"
        )
        category_groups = {
            (category.taxonomy_version, category.main_type) for category in categories
        }
        if len(category_groups) > 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "category_ids must belong to one taxonomy version and main category"
                ),
            )

        job = JobPosting(
            name=storage_key,
            source_key=storage_key,
            company_id=data.company_id,
            title=data.title,
            raw_description=data.description,
            requirements=data.requirements,
            department=data.department,
            employment_type=data.employment_type,
            seniority_level=data.seniority_level,
            posted_date=data.posted_date,
            source_platform=data.source_platform,
            source_job_id=data.source_job_id,
            source_url=str(data.source_url) if data.source_url else None,
            extraction_confidence=data.extraction_confidence,
            salary_min=data.salary_min,
            salary_max=data.salary_max,
            salary_average=data.salary_average,
            salary_currency=data.salary_currency,
            salary_period=data.salary_period.value if data.salary_period else None,
            salary_source=data.salary_source,
            ingested_at=datetime.now(timezone.utc),
            locations=locations,
            skills=skills,
            categories=categories,
        )
        db.add(job)
        db.commit()
        return get_job(db, job.job_id)
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        if _is_unique_violation(exc):
            logger.info("Duplicate job rejected for source_key=%s", data.source_key)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Job already exists for source_key: {data.source_key}",
            ) from exc
        logger.exception("Database error creating source_key=%s", data.source_key)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create job",
        ) from exc
    except Exception as exc:
        db.rollback()
        logger.exception("Unable to create job for source_key=%s", data.source_key)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create job",
        ) from exc
