import re
from datetime import datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")
PHONE_PATTERN = re.compile(r"^\+?[0-9 ()-]{7,32}$")


def validate_password_strength(value: str) -> str:
    requirements = (
        (r"[a-z]", "a lowercase letter"),
        (r"[A-Z]", "an uppercase letter"),
        (r"\d", "a number"),
        (r"[^A-Za-z0-9]", "a special character"),
    )
    missing = [
        label for pattern, label in requirements if not re.search(pattern, value)
    ]
    if missing:
        raise ValueError("password must contain " + ", ".join(missing))
    return value


def normalize_username(value: str) -> str:
    normalized = value.strip().lower()
    if len(normalized) < 3:
        raise ValueError("username must contain at least 3 characters")
    if not USERNAME_PATTERN.fullmatch(normalized):
        raise ValueError(
            "username may contain only letters, numbers, dots, hyphens, "
            "and underscores"
        )
    return normalized


def normalize_full_name(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("full name must not be empty")
    return normalized


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
        return normalize_username(value)

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str) -> str:
        return normalize_full_name(value)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return validate_password_strength(value)


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


class UserProfileResponse(UserResponse):
    phone: str | None = None
    address: str | None = None


class UserProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr | None = None
    username: str | None = Field(default=None, min_length=3, max_length=50)
    full_name: str | None = Field(default=None, min_length=1, max_length=120)
    phone: str | None = Field(default=None, max_length=32)
    address: str | None = Field(default=None, max_length=500)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr | None) -> str | None:
        return str(value).strip().lower() if value is not None else None

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str | None) -> str | None:
        return normalize_username(value) if value is not None else None

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str | None) -> str | None:
        return normalize_full_name(value) if value is not None else None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.split())
        if normalized and not PHONE_PATTERN.fullmatch(normalized):
            raise ValueError(
                "phone must contain a valid international or local number"
            )
        return normalized or None

    @field_validator("address")
    @classmethod
    def normalize_address(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.split())
        return normalized or None

    @model_validator(mode="after")
    def validate_patch(self):
        if not self.model_fields_set:
            raise ValueError("at least one profile field must be provided")
        for required_field in ("email", "username", "full_name"):
            if (
                required_field in self.model_fields_set
                and getattr(self, required_field) is None
            ):
                raise ValueError(f"{required_field} cannot be null")
        return self


class PasswordChangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        return validate_password_strength(value)


class AuthResponse(BaseModel):
    user: UserResponse
    token_type: str = "bearer"
    expires_in: int
