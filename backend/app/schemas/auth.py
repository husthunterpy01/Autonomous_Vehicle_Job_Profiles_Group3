import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")


class SignUpRequest(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=50)
    full_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=12, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        normalized = value.strip().lower()
        if len(normalized) < 3:
            raise ValueError("username must contain at least 3 characters")
        if not USERNAME_PATTERN.fullmatch(normalized):
            raise ValueError(
                "username may contain only letters, numbers, dots, hyphens, "
                "and underscores"
            )
        return normalized

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("full name must not be empty")
        return normalized

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        requirements = (
            (r"[a-z]", "a lowercase letter"),
            (r"[A-Z]", "an uppercase letter"),
            (r"\d", "a number"),
            (r"[^A-Za-z0-9]", "a special character"),
        )
        missing = [label for pattern, label in requirements if not re.search(pattern, value)]
        if missing:
            raise ValueError("password must contain " + ", ".join(missing))
        return value


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=1, max_length=128)
    remember_me: bool = False

    @field_validator("identifier")
    @classmethod
    def normalize_identifier(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("email or username is required")
        return normalized


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    email: EmailStr
    username: str
    full_name: str
    created_at: datetime


class AuthResponse(BaseModel):
    user: UserResponse
    token_type: str = "bearer"
    expires_in: int
