from typing import Optional
from uuid import UUID

from pydantic import BaseModel, validator


class CompanyCreate(BaseModel):
    name: Optional[str] = None
    website_url: Optional[str] = None
    career_page_url: Optional[str] = None
    company_type: Optional[str] = None
    datasource_status: Optional[str] = None

    @validator("name")
    def normalize_name(cls, value):
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("Company name cannot be empty")
        return value


class CompanyResponse(BaseModel):
    company_id: UUID
    name: str
    website_url: Optional[str] = None
    career_page_url: Optional[str] = None
    company_type: Optional[str] = None
    datasource_status: Optional[str] = None


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
