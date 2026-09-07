from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.auth import SignUpRequest
from app.utils.security import DUMMY_PASSWORD_HASH, SecurityService


class DuplicateUserError(Exception):
    pass


class AuthService:
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
            raise DuplicateUserError from error
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
