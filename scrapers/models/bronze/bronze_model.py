from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class RawPayload:
    source: str
    company: str
    source_system: str | None
    url: str
    status: int
    content_type: str
    body: bytes
    fetched_at: datetime


