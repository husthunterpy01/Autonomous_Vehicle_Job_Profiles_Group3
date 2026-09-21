from secrets import compare_digest
from typing import Annotated

from fastapi import Header, HTTPException, status

from app.core.config import settings


def require_job_write_key(
    write_key: Annotated[str | None, Header(alias="X-Job-Write-Key")] = None,
) -> None:
    """Fail closed when the internal job-write credential is not configured."""
    configured_key = settings.job_write_api_key
    if not configured_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Job write API is not configured",
        )
    if write_key is None or not compare_digest(write_key, configured_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing job write API key",
        )
