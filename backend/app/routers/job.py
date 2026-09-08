from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.models import Category, Company, JobPosting, Location, Skill
from app.schemas.job import JobResponse
from app.utils.pagination import PageResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])


def to_response(job):
    return JobResponse(
        job_id=job.job_id, title=job.title, company_id=job.company_id,
        company_name=job.company.name,
        locations=sorted(location.name for location in job.locations),
        skills=sorted(skill.skill_name for skill in job.skills),
        categories=[dict(category_id=c.category_id, main_type=c.main_type, sub_type=c.sub_type, taxonomy_version=c.taxonomy_version)
                    for c in sorted(job.categories, key=lambda c: (c.taxonomy_version, c.normalized_name))],
        employment_type=job.employment_type, raw_description=job.raw_description,
        source_url=job.source_url, posted_date=job.posted_date,
    )


def job_query(db):
    return db.query(JobPosting).options(
        selectinload(JobPosting.company), selectinload(JobPosting.locations), selectinload(JobPosting.skills),
        selectinload(JobPosting.categories)
    )


@router.get("", response_model=PageResponse[JobResponse])
def list_jobs(
    q: str | None = None,
    location: str | None = None,
    skill: str | None = None,
    category_id: UUID | None = None,
    company_id: UUID | None = None,
    employment_type: int | None = Query(None, ge=1, le=6),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
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
        query = query.filter(JobPosting.employment_type == employment_type)
    query = query.order_by(JobPosting.posted_date.desc().nullslast(), JobPosting.job_id)
    total = query.count()
    jobs = query.offset((page - 1) * page_size).limit(page_size).all()
    return PageResponse(items=[to_response(job) for job in jobs], total=total, page=page, page_size=page_size, total_pages=(total + page_size - 1) // page_size)


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: UUID, db: Session = Depends(get_db)):
    job = job_query(db).filter(JobPosting.job_id == job_id).one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return to_response(job)
