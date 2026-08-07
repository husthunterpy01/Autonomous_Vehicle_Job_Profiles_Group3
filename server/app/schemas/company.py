from uuid import UUID

from pydantic import BaseModel, validator


class CompanyCreate(BaseModel):
    name: str | None = None
    website_url: str | None = None
    career_page_url: str | None = None
    company_type: str | None = None
    datasource_status: str | None = None

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
    website_url: str | None = None
    career_page_url: str | None = None
    company_type: str | None = None
    datasource_status: str | None = None


class CompanyUpdate(BaseModel):
    name: str | None = None
