from datetime import datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models import Company, CompanyLocation, JobPosting
from app.core.database import Base


@pytest.fixture
def db_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


def make_company(
    name: str,
    *,
    company_id: UUID | None = None,
    company_type: str = "AV_Startup",
) -> Company:
    suffix = (company_id or uuid4()).hex[:8]
    return Company(
        company_id=company_id or uuid4(),
        name=name,
        company_type=company_type,
        website_url=f"https://{suffix}.example.com",
        career_page_url=f"https://{suffix}.example.com/careers",
        datasource_status="confirmed",
    )


def make_location(
    company: Company,
    *,
    country: str = "United States",
    city: str = "San Francisco",
    is_hq: bool = True,
) -> CompanyLocation:
    return CompanyLocation(
        location_id=uuid4(),
        country=country,
        city=city,
        is_hq=is_hq,
        company=company,
    )


def make_job(
    company: Company,
    *,
    name: str | None = None,
    title: str = "Software Engineer",
) -> JobPosting:
    suffix = uuid4().hex[:8]
    return JobPosting(
        job_id=uuid4(),
        name=name or f"{company.name.lower().replace(' ', '-')}-{suffix}",
        title=title,
        department="Engineering",
        employment_type=1,
        job_location="Remote",
        seniority_level=2,
        salary_average=150000,
        salary_currency="USD",
        raw_description="Build autonomous systems.",
        posted_date=datetime(2026, 8, 1, 12, 0, 0),
        source_platform="Greenhouse",
        extraction_confidence=0.9,
        company_id=company.company_id,
    )


def seed_companies_with_jobs(db: Session) -> dict[str, Company]:
    alpha = make_company("Alpha Robotics")
    beta = make_company("Beta AV")
    gamma = make_company("Gamma Drive")

    db.add_all([alpha, beta, gamma])
    db.add(make_location(alpha, country="United States", city="Austin"))
    db.add(make_location(beta, country="Canada", city="Toronto"))
    db.add_all(
        [
            make_job(alpha, name="alpha-job-1"),
            make_job(alpha, name="alpha-job-2"),
            make_job(beta, name="beta-job-1"),
        ]
    )
    db.commit()

    return {"alpha": alpha, "beta": beta, "gamma": gamma}
