from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass(frozen=True)
class BronzePayload:
    ats_name: Optional[str]
    company_name: str
    job_name: str
    job_description: str
    headquarter: Optional[str]
    location: Optional[str]
    job_url: Optional[str]
    job_uploaded_at: datetime
    employment_type: str
    id: Optional[int] = None
