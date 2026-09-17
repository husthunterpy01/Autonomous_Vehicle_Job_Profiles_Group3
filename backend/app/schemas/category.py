from uuid import UUID

from pydantic import BaseModel


class CategoryStatResponse(BaseModel):
    category_id: UUID
    sub_type: str
    main_type: str | None
    job_count: int
