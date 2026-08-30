from dataclasses import dataclass, field
from datetime import datetime

@dataclass(frozen=True)
class RawPayload:
    source: str
    company: str
    url: str
    status: int
    content_type: str
    body: bytes
    fetched_at: datetime
    request: dict = field(default_factory=dict) 
