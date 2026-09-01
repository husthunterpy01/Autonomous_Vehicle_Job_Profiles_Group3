from dataclasses import dataclass, field
from datetime import datetime

@dataclass(frozen=True)
class JobPosting:
    source: str
    company: str
    source_job_id: str
    title: str
    canonical_job_url: str | None = None
    apply_url: str | None = None
    requisition_id: str | None = None
    locations: tuple[str, ...] = ()
    country_code: str | None = None
    department: str | None = None
    team: str | None = None
    employment_type: str | None = None
    workplace_type: str | None = None
    description_html: str | None = None
    description_text: str | None = None
    published_at: datetime | None = None
    updated_at: datetime | None = None
    retrieved_at: datetime | None = None