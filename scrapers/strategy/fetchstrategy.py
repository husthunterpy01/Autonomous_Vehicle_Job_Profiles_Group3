from __future__ import annotations
 
from abc import ABC, abstractmethod
from typing import Any
 
 
class FetchStrategy(ABC):
    
    @abstractmethod
    def fetch_postings(self, max_jobs: int, timeout: float = 30.0) -> list[dict[str, Any]]:
        """Return up to max_jobs raw job postings, exactly as the source
        (API response or rendered page) returned them
        """
        pass