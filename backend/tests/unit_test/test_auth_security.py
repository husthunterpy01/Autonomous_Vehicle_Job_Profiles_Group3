import sqlite3
from datetime import timedelta
from unittest.mock import MagicMock
from uuid import uuid4

import jwt
import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.core.config import Settings, settings
from app.schemas.auth import SignUpRequest
from app.services.auth import AuthService, DuplicateUserError
from app.services.rate_limit import LoginRateLimiter
from app.utils.security import SecurityService


def test_password_hash_never_contains_plaintext_password():
    password = "SecurePassword!123"

    encoded = SecurityService.hash_password(password)

    assert password not in encoded
    assert SecurityService.verify_password(password, encoded)
    assert not SecurityService.verify_password("WrongPassword!123", encoded)


@pytest.mark.parametrize(
    "password",
    [
        "Short!1",
        "NOLOWERCASE!123",
        "nouppercase!123",
        "NoNumbersHere!",
        "NoSpecialCharacter123",
    ],
)
def test_signup_rejects_weak_passwords(password):
    with pytest.raises(ValidationError):
        SignUpRequest(
            email="driver@example.com",
            username="driver",
            full_name="Driver Engineer",
            password=password,
        )


def test_signup_rejects_username_that_is_too_short_after_trimming():
    with pytest.raises(ValidationError):
        SignUpRequest(
            email="driver@example.com",
            username="  a  ",
            full_name="Driver Engineer",
            password="SecurePassword!123",
        )


def test_jwt_contains_only_minimal_authentication_claims():
    user_id = uuid4()
    token = SecurityService.create_access_token(user_id, timedelta(minutes=5))

    payload = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )

    assert set(payload) == {"sub", "type", "iat", "exp"}
    assert payload["sub"] == str(user_id)
    assert SecurityService.decode_access_token(token) == user_id


def test_rate_limiter_blocks_at_configured_limit_and_can_be_cleared():
    limiter = LoginRateLimiter(max_attempts=2, window_seconds=60)

    assert limiter.retry_after("client:user") is None
    limiter.record_failure("client:user")
    limiter.record_failure("client:user")
    assert limiter.retry_after("client:user") is not None

    limiter.clear("client:user")
    assert limiter.retry_after("client:user") is None


def test_non_development_environment_requires_jwt_secret(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)

    with pytest.raises(RuntimeError, match="outside the development environment"):
        Settings()


class DatabaseError(Exception):
    def __init__(self, sqlstate: str):
        self.sqlstate = sqlstate


def make_integrity_error(sqlstate: str) -> IntegrityError:
    return IntegrityError(
        "INSERT INTO user_account ...",
        {},
        DatabaseError(sqlstate),
    )


def test_unique_violation_is_reported_as_duplicate_account():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    db.commit.side_effect = make_integrity_error("23505")
    data = SignUpRequest(
        email="driver@example.com",
        username="driver",
        full_name="Driver Engineer",
        password="SecurePassword!123",
    )

    with pytest.raises(DuplicateUserError):
        AuthService.create_user(db, data)

    db.rollback.assert_called_once_with()


def test_non_unique_integrity_error_is_not_reported_as_duplicate_account():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    database_error = make_integrity_error("23503")
    db.commit.side_effect = database_error
    data = SignUpRequest(
        email="driver@example.com",
        username="driver",
        full_name="Driver Engineer",
        password="SecurePassword!123",
    )

    with pytest.raises(IntegrityError) as raised:
        AuthService.create_user(db, data)

    assert raised.value is database_error
    db.rollback.assert_called_once_with()


def test_sqlite_unique_violation_is_detected_without_extended_error_attributes():
    error = IntegrityError(
        "INSERT INTO user_account ...",
        {},
        sqlite3.IntegrityError(
            "UNIQUE constraint failed: user_account.email"
        ),
    )

    assert AuthService._is_unique_violation(error)
