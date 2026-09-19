from uuid import UUID

from pydantic import BaseModel


class SkillStatResponse(BaseModel):
    skill_id: UUID
    skill_name: str
    number_of_occurrences: int
