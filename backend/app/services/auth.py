import logging
import sqlite3

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.auth import SignUpRequest, UserProfileUpdate
from app.utils.security import DUMMY_PASSWORD_HASH, SecurityService


class DuplicateUserError(Exception):
    pass


class IncorrectCurrentPasswordError(Exception):
    pass


class ReusedPasswordError(Exception):
    pass


logger = logging.getLogger(__name__)


class AuthService:
    @staticmethod
    def _is_unique_violation(error: IntegrityError) -> bool:
        original_error = error.orig
        sqlstate = getattr(original_error, "sqlstate", None) or getattr(
            original_error, "pgcode", None
        )
        if sqlstate == "23505":
            return True

        sqlite_error_code = getattr(original_error, "sqlite_errorcode", None)
        if sqlite_error_code in {1555, 2067}:
            return True
        return isinstance(original_error, sqlite3.IntegrityError) and str(
            original_error
        ).startswith("UNIQUE constraint failed:")

    @staticmethod
    def create_user(db: Session, data: SignUpRequest) -> User:
        duplicate = (
            db.query(User)
            .filter(or_(User.email == data.email, User.username == data.username))
            .first()
        )
        if duplicate:
            raise DuplicateUserError

        user = User(
            email=data.email,
            username=data.username,
            full_name=data.full_name,
            password_hash=SecurityService.hash_password(data.password),
        )
        db.add(user)
        try:
            db.commit()
        except IntegrityError as error:
            db.rollback()
            if AuthService._is_unique_violation(error):
                raise DuplicateUserError from error
            raise
        db.refresh(user)
        return user

    @staticmethod
    def authenticate(db: Session, identifier: str, password: str) -> User | None:
        user = (
            db.query(User)
            .filter(or_(User.email == identifier, User.username == identifier))
            .first()
        )
        stored_hash = user.password_hash if user else DUMMY_PASSWORD_HASH
        password_matches = SecurityService.verify_password(password, stored_hash)
        if not user or not user.is_active or not password_matches:
            return None
        return user

    @staticmethod
    def update_profile(db: Session, user: User, data: UserProfileUpdate) -> User:
        changes = data.model_dump(exclude_unset=True)
        identity_filters = []
        if "email" in changes:
            identity_filters.append(User.email == changes["email"])
        if "username" in changes:
            identity_filters.append(User.username == changes["username"])

        if identity_filters:
            duplicate = (
                db.query(User)
                .filter(User.user_id != user.user_id, or_(*identity_filters))
                .first()
            )
            if duplicate:
                raise DuplicateUserError

        for field, value in changes.items():
            setattr(user, field, value)

        try:
            db.commit()
        except IntegrityError as error:
            db.rollback()
            if AuthService._is_unique_violation(error):
                raise DuplicateUserError from error
            raise
        db.refresh(user)
        logger.info(
            "User profile updated",
            extra={"user_id": str(user.user_id), "updated_fields": sorted(changes)},
        )
        return user

    @staticmethod
    def change_password(
        db: Session,
        user: User,
        current_password: str,
        new_password: str,
    ) -> None:
        if not SecurityService.verify_password(current_password, user.password_hash):
            raise IncorrectCurrentPasswordError
        if SecurityService.verify_password(new_password, user.password_hash):
            raise ReusedPasswordError

        user.password_hash = SecurityService.hash_password(new_password)
        db.commit()
        logger.info(
            "User password changed",
            extra={"user_id": str(user.user_id)},
        )
