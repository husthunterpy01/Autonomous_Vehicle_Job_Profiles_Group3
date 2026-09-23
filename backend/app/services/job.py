import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, defer, joinedload, selectinload

from app.enums.job_sort_field import JobSortField
from app.enums.sort_direction import SortDirection
from app.models import Category, Company, JobPosting, Location, Skill
from app.schemas.job import CategoryResponse, JobCreate, JobDetailResponse, JobResponse
from app.services.category_sync import dominant_categories
from app.utils.normalization import normalized
from app.utils.pagination import PageResponse

logger = logging.getLogger(__name__)


class JobManagementError(Exception):
    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


class JobEntityNotFoundError(JobManagementError):
    pass


class DuplicateJobError(JobManagementError):
    pass


class InvalidJobDataError(JobManagementError):
    pass


class JobPersistenceError(JobManagementError):
    pass


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
        sub_types=[{"category_id": c.category_id, "sub_type": c.sub_type} for c in members],
    )


def to_response(job, *, include_body: bool = True):
    return JobResponse(
        job_id=job.job_id, title=job.title, company_id=job.company_id,
        company_name=job.company.name,
        locations=sorted(location.name for location in job.locations),
        skills=sorted(skill.skill_name for skill in job.skills),
        category=_to_category_response(job.categories),
        employment_type=job.employment_type,
        raw_description=job.raw_description if include_body else None,
        source_url=job.source_url, posted_date=job.posted_date,
        salary_min=job.salary_min, salary_max=job.salary_max, salary_average=job.salary_average,
        salary_currency=job.salary_currency, salary_period=job.salary_period, salary_source=job.salary_source,
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
        selectinload(JobPosting.company), selectinload(JobPosting.locations), selectinload(JobPosting.skills),
        selectinload(JobPosting.categories)
    )


# One JOIN query for company + collections. selectinload would be a round
# trip per relationship, and each of those is ~250ms to the hosted DB.
_LIST_LOAD = (
    defer(JobPosting.raw_description),
    defer(JobPosting.requirements),
    joinedload(JobPosting.company),
    joinedload(JobPosting.locations),
    joinedload(JobPosting.skills),
    joinedload(JobPosting.categories),
)
_DETAIL_LOAD = (
    joinedload(JobPosting.company),
    joinedload(JobPosting.locations),
    joinedload(JobPosting.skills),
    joinedload(JobPosting.categories),
)


# Newest first reads best for dates; A-Z for names. Each entry is the
# default direction plus the column to order by. Company is sorted by the
# company name rather than its UUID, so the join below is required.
_SORT_COLUMNS = {
    JobSortField.POSTED_DATE: (SortDirection.DESC, JobPosting.posted_date),
    JobSortField.TITLE: (SortDirection.ASC, func.lower(JobPosting.title)),
    JobSortField.COMPANY: (SortDirection.ASC, func.lower(Company.name)),
}


def _sort_join(query, sort: JobSortField):
    if sort is JobSortField.COMPANY:
        # LEFT JOIN, not an inner join: company_id is NOT NULL today, but if
        # that ever changed a job without a company should sort last like any
        # other missing value instead of silently dropping out of the list.
        # Many-to-one either way, so this cannot duplicate job rows.
        return query.outerjoin(Company, JobPosting.company_id == Company.company_id)
    return query


def _sort_clauses(sort: JobSortField, direction: SortDirection | None):
    default_direction, column = _SORT_COLUMNS[sort]
    ordering = column.desc() if (direction or default_direction) is SortDirection.DESC else column.asc()
    # Jobs missing the sorted value go last whichever direction is chosen,
    # so an empty column never occupies the first page. job_id breaks ties
    # so a row cannot drift between pages while paginating.
    return ordering.nullslast(), JobPosting.job_id


def _apply_sort(query, sort: JobSortField, direction: SortDirection | None):
    return _sort_join(query, sort).order_by(*_sort_clauses(sort, direction))


def list_jobs(
    db: Session, *, q: str | None = None, location: str | None = None, skill: str | None = None,
    category_id: UUID | None = None, company_id: UUID | None = None, employment_type: int | None = None,
    min_salary: float | None = None, max_salary: float | None = None, salary_period: str | None = None,
    has_salary: bool | None = None, sort: JobSortField = JobSortField.POSTED_DATE,
    direction: SortDirection | None = None, page: int = 1, page_size: int = 10,
):
    query = db.query(JobPosting)
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
        condition = JobPosting.salary_min.isnot(None) | JobPosting.salary_average.isnot(None)
        query = query.filter(condition if has_salary else ~condition)
    # Page of ids + total in one statement (window count, no TOAST columns),
    # then one joined load of those rows. Two round-trips instead of a
    # count + page + four selectinload queries.
    id_rows = (
        _apply_sort(query, sort, direction)
        .with_entities(
            JobPosting.job_id,
            func.count(JobPosting.job_id).over().label("total"),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    if not id_rows:
        return PageResponse(
            items=[], total=0, page=page, page_size=page_size, total_pages=0,
        )
    job_ids = [row.job_id for row in id_rows]
    total = int(id_rows[0].total)
    order = {job_id: index for index, job_id in enumerate(job_ids)}
    jobs = (
        db.execute(
            select(JobPosting)
            .options(*_LIST_LOAD)
            .where(JobPosting.job_id.in_(job_ids))
        )
        .unique()
        .scalars()
        .all()
    )
    jobs.sort(key=lambda job: order[job.job_id])
    return PageResponse(
        items=[to_response(job, include_body=False) for job in jobs],
        total=total, page=page, page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


def get_job(db: Session, job_id: UUID) -> JobDetailResponse | None:
    job = (
        db.execute(
            select(JobPosting)
            .options(*_DETAIL_LOAD)
            .where(JobPosting.job_id == job_id)
        )
        .unique()
        .scalars()
        .one_or_none()
    )
    return to_detail_response(job) if job is not None else None


def _load_related(db: Session, model, id_column, ids: list[UUID], label: str):
    if not ids:
        return []
    rows = db.query(model).filter(id_column.in_(ids)).all()
    found = {getattr(row, id_column.key) for row in rows}
    missing = [str(item_id) for item_id in ids if item_id not in found]
    if missing:
        raise JobEntityNotFoundError(
            f"Unknown {label} IDs: {', '.join(missing)}"
        )
    return rows


def _is_duplicate_job_violation(exc: IntegrityError) -> bool:
    original = getattr(exc, "orig", None)
    sqlstate = getattr(original, "sqlstate", None) or getattr(original, "pgcode", None)
    constraint = getattr(getattr(original, "diag", None), "constraint_name", None)
    message = str(original).lower()
    return (
        sqlstate == "23505"
        and constraint in {"jobposting_name_key", "jobposting_source_key_key"}
    ) or (
        "unique constraint" in message
        and ("jobposting.name" in message or "jobposting.source_key" in message)
    )


def _merge_locations(db: Session, linked: list[Location], names: list[str]):
    by_key = {location.normalized_name: location for location in linked}
    for name in names:
        key = normalized(name)
        location = by_key.get(key)
        if location is None:
            location = db.query(Location).filter_by(normalized_name=key).one_or_none()
        if location is None:
            location = Location(name=name, normalized_name=key)
            db.add(location)
            db.flush()
        by_key[key] = location
    return list(by_key.values())


def _merge_skills(db: Session, linked: list[Skill], specs):
    by_key = {(skill.normalized_name, skill.skill_type): skill for skill in linked}
    for spec in specs:
        key = (normalized(spec.name), spec.skill_type.value)
        skill = by_key.get(key)
        if skill is None:
            skill = db.query(Skill).filter_by(
                normalized_name=key[0], skill_type=key[1]
            ).one_or_none()
        if skill is None:
            skill = Skill(
                skill_name=spec.name,
                normalized_name=key[0],
                skill_type=key[1],
            )
            db.add(skill)
            db.flush()
        by_key[key] = skill
    return list(by_key.values())


def _merge_categories(db: Session, linked: list[Category], specs):
    by_key = {
        (category.taxonomy_version, category.normalized_name): category
        for category in linked
    }
    for spec in specs:
        key = (spec.taxonomy_version, normalized(spec.sub_type))
        category = by_key.get(key)
        if category is None:
            category = db.query(Category).filter_by(
                taxonomy_version=key[0], normalized_name=key[1]
            ).one_or_none()
        if category is None:
            category = Category(
                main_type=spec.main_type,
                sub_type=spec.sub_type,
                normalized_name=key[1],
                taxonomy_version=key[0],
            )
            db.add(category)
            db.flush()
        elif category.main_type != spec.main_type:
            raise InvalidJobDataError(
                f"Category {spec.sub_type} already belongs to main category "
                f"{category.main_type}"
            )
        by_key[key] = category
    return list(by_key.values())


def create_job(db: Session, data: JobCreate) -> JobDetailResponse:
    """Create one system-supplied job and link existing taxonomy entities.

    The caller provides a stable source_key. Prefixing it keeps this write
    channel's namespace separate from keys produced by the Silver importer.
    """
    storage_key = f"api:{data.source_key}"
    try:
        if db.get(Company, data.company_id) is None:
            raise JobEntityNotFoundError(f"Company not found: {data.company_id}")
        if (
            db.query(JobPosting).filter(JobPosting.source_key == storage_key).first()
            is not None
        ):
            raise DuplicateJobError(
                f"Job already exists for source_key: {data.source_key}"
            )

        locations = _load_related(
            db, Location, Location.location_id, data.location_ids, "location"
        )
        skills = _load_related(db, Skill, Skill.skill_id, data.skill_ids, "skill")
        categories = _load_related(
            db, Category, Category.category_id, data.category_ids, "category"
        )
        locations = _merge_locations(db, locations, data.locations)
        skills = _merge_skills(db, skills, data.skills)
        categories = _merge_categories(db, categories, data.categories)
        category_groups = {
            (category.taxonomy_version, category.main_type) for category in categories
        }
        if len(category_groups) > 1:
            raise InvalidJobDataError(
                "categories must belong to one taxonomy version and main category"
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
            salary_source=data.salary_source.value if data.salary_source else None,
            ingested_at=datetime.now(timezone.utc),
            locations=locations,
            skills=skills,
            categories=categories,
        )
        db.add(job)
        db.commit()
        return get_job(db, job.job_id)
    except JobManagementError:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        if _is_duplicate_job_violation(exc):
            logger.info("Duplicate job rejected for source_key=%s", data.source_key)
            raise DuplicateJobError(
                f"Job already exists for source_key: {data.source_key}"
            ) from exc
        logger.exception("Database error creating source_key=%s", data.source_key)
        raise JobPersistenceError("Unable to create job") from exc
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Database error creating source_key=%s", data.source_key)
        raise JobPersistenceError("Unable to create job") from exc
