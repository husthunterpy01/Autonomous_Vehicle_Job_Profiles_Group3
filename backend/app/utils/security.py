import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from jwt import InvalidTokenError
from pwdlib import PasswordHash

from app.core.config import settings

password_hash = PasswordHash.recommended()
DUMMY_PASSWORD_HASH = password_hash.hash("NotARealPassword!123")


class SecurityService:
    @staticmethod
    def hash_password(password: str) -> str:
        return password_hash.hash(password)

    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        try:
            return password_hash.verify(password, hashed_password)
        except (TypeError, ValueError):
            return False

    @staticmethod
    def create_access_token(
        user_id: UUID | str,
        expires_delta: timedelta,
        token_version: int = 0,
    ) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(user_id),
            "type": "access",
            "ver": token_version,
            "iat": now,
            "exp": now + expires_delta,
        }
        return jwt.encode(
            payload,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )

    @staticmethod
    def decode_access_token(token: str) -> UUID:
        user_id, _ = SecurityService.decode_access_token_with_version(token)
        return user_id

    @staticmethod
    def decode_access_token_with_version(token: str) -> tuple[UUID, int]:
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )
            if payload.get("type") != "access":
                raise InvalidTokenError("incorrect token type")
            token_version = payload.get("ver", 0)
            if not isinstance(token_version, int) or token_version < 0:
                raise InvalidTokenError("invalid token version")
            return UUID(payload["sub"]), token_version
        except (InvalidTokenError, KeyError, TypeError, ValueError) as error:
            raise ValueError("invalid or expired access token") from error

    @staticmethod
    def generate_password_reset_token() -> str:
        return secrets.token_urlsafe(32)

    @staticmethod
    def hash_password_reset_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def hash_rate_limit_key(value: str) -> str:
        return hashlib.sha256(value.strip().lower().encode("utf-8")).hexdigest()
