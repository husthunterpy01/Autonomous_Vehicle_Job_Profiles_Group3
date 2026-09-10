"""Reusable validation for opaque external identifiers."""


def require_identifier(value, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value
