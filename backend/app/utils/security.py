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
    def create_access_token(user_id: UUID | str, expires_delta: timedelta) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(user_id),
            "type": "access",
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
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )
            if payload.get("type") != "access":
                raise InvalidTokenError("incorrect token type")
            return UUID(payload["sub"])
        except (InvalidTokenError, KeyError, TypeError, ValueError) as error:
            raise ValueError("invalid or expired access token") from error
