import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.password_reset_token import PasswordResetToken
from app.models.user import User
from app.utils.security import SecurityService

logger = logging.getLogger(__name__)


class InvalidResetTokenError(Exception):
    pass


class ExpiredResetTokenError(Exception):
    pass


class UsedResetTokenError(Exception):
    pass


class ReusedPasswordError(Exception):
    pass


@dataclass(frozen=True)
class IssuedPasswordReset:
    user: User
    token: str


class PasswordResetService:
    @staticmethod
    def _utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @staticmethod
    def _validate_record(
        record: PasswordResetToken | None,
        now: datetime,
    ) -> PasswordResetToken:
        if record is None:
            raise InvalidResetTokenError
        if record.used_at is not None:
            raise UsedResetTokenError
        if PasswordResetService._utc(record.expires_at) <= now:
            raise ExpiredResetTokenError
        return record

    @staticmethod
    def request_reset(db: Session, identifier: str) -> IssuedPasswordReset | None:
        user = (
            db.query(User)
            .filter(or_(User.email == identifier, User.username == identifier))
            .first()
        )
        if not user or not user.is_active:
            # Do comparable token work without persisting anything. The API response
            # remains identical, which avoids revealing whether the account exists.
            SecurityService.hash_password_reset_token(
                SecurityService.generate_password_reset_token()
            )
            return None

        now = datetime.now(timezone.utc)
        db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user.user_id,
            PasswordResetToken.used_at.is_(None),
        ).update({PasswordResetToken.used_at: now}, synchronize_session=False)

        token = SecurityService.generate_password_reset_token()
        record = PasswordResetToken(
            user_id=user.user_id,
            token_hash=SecurityService.hash_password_reset_token(token),
            expires_at=now + timedelta(minutes=settings.password_reset_token_minutes),
        )
        db.add(record)
        db.commit()
        logger.info(
            "Password reset requested for account",
            extra={"user_id": str(user.user_id)},
        )
        return IssuedPasswordReset(user=user, token=token)

    @staticmethod
    def revoke_token(db: Session, token: str) -> None:
        now = datetime.now(timezone.utc)
        token_hash = SecurityService.hash_password_reset_token(token)
        db.query(PasswordResetToken).filter(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used_at.is_(None),
        ).update({PasswordResetToken.used_at: now}, synchronize_session=False)
        db.commit()

    @staticmethod
    def verify_token(db: Session, token: str) -> PasswordResetToken:
        token_hash = SecurityService.hash_password_reset_token(token)
        record = (
            db.query(PasswordResetToken)
            .filter(PasswordResetToken.token_hash == token_hash)
            .first()
        )
        return PasswordResetService._validate_record(
            record,
            datetime.now(timezone.utc),
        )

    @staticmethod
    def reset_password(db: Session, token: str, new_password: str) -> User:
        now = datetime.now(timezone.utc)
        token_hash = SecurityService.hash_password_reset_token(token)
        record = (
            db.query(PasswordResetToken)
            .filter(PasswordResetToken.token_hash == token_hash)
            .with_for_update()
            .first()
        )
        record = PasswordResetService._validate_record(record, now)
        user = db.get(User, record.user_id)
        if not user or not user.is_active:
            raise InvalidResetTokenError
        if SecurityService.verify_password(new_password, user.password_hash):
            raise ReusedPasswordError

        user.password_hash = SecurityService.hash_password(new_password)
        user.token_version += 1
        db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user.user_id,
            PasswordResetToken.used_at.is_(None),
        ).update({PasswordResetToken.used_at: now}, synchronize_session=False)
        db.commit()
        db.refresh(user)
        logger.info(
            "Password reset completed and sessions invalidated",
            extra={"user_id": str(user.user_id)},
        )
        return user
