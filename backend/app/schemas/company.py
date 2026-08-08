from uuid import UUID

from pydantic import BaseModel, validator


class CompanyCreate(BaseModel):
    name: str
    website_url: str
    career_page_url: str
    company_type: str
    datasource_status: str

    @validator("name", "website_url", "career_page_url", "company_type", "datasource_status")
    def normalize_required_str(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("must not be empty")
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
