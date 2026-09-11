from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.auth import AuthResponse, LoginRequest, SignUpRequest, UserResponse
from app.services.auth import AuthService, DuplicateUserError
from app.services.rate_limit import LoginRateLimiter
from app.utils.security import SecurityService

router = APIRouter(prefix="/auth", tags=["authentication"])
DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]

login_rate_limiter = LoginRateLimiter(
    max_attempts=settings.auth_login_max_attempts,
    window_seconds=settings.auth_login_window_seconds,
)


def _set_access_cookie(
    response: Response, user: User, *, remember_me: bool
) -> int:
    if remember_me:
        expires_delta = timedelta(days=settings.jwt_remember_days)
        max_age = int(expires_delta.total_seconds())
    else:
        expires_delta = timedelta(minutes=settings.jwt_access_token_minutes)
        max_age = None

    token = SecurityService.create_access_token(user.user_id, expires_delta)
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        max_age=max_age,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        path="/",
    )
    return int(expires_delta.total_seconds())


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def sign_up(data: SignUpRequest, response: Response, db: DbSession):
    try:
        user = AuthService.create_user(db, data)
    except DuplicateUserError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with that email or username already exists",
        ) from error
    expires_in = _set_access_cookie(response, user, remember_me=False)
    return AuthResponse(user=user, expires_in=expires_in)


@router.post("/login", response_model=AuthResponse)
def sign_in(
    data: LoginRequest,
    request: Request,
    response: Response,
    db: DbSession,
):
    client_host = request.client.host if request.client else "unknown"
    rate_limit_key = f"{client_host}:{data.identifier}"
    retry_after = login_rate_limiter.retry_after(rate_limit_key)
    if retry_after is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many sign-in attempts. Please try again later",
            headers={"Retry-After": str(retry_after)},
        )

    user = AuthService.authenticate(db, data.identifier, data.password)
    if not user:
        login_rate_limiter.record_failure(rate_limit_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password",
        )

    login_rate_limiter.clear(rate_limit_key)
    expires_in = _set_access_cookie(
        response,
        user,
        remember_me=data.remember_me,
    )
    return AuthResponse(user=user, expires_in=expires_in)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def sign_out(response: Response):
    response.delete_cookie(
        key=settings.auth_cookie_name,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        path="/",
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: CurrentUser):
    return current_user
