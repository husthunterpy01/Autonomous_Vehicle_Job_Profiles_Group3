from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.main import app
from app.models.password_reset_token import PasswordResetToken
from app.models.user import User
from app.services.email import get_password_reset_email_sender
from app.utils.security import SecurityService

SIGNUP_PAYLOAD = {
    "email": "Driver.Engineer@example.com",
    "username": "DriverEngineer",
    "full_name": "Driver Engineer",
    "password": "SecurePassword!123",
}


class RecordingEmailSender:
    def __init__(self):
        self.reset_emails: list[tuple[str, str]] = []
        self.changed_emails: list[str] = []

    def send_reset_link(self, user, token: str) -> None:
        self.reset_emails.append((user.email, token))

    def send_password_changed(self, user) -> None:
        self.changed_emails.append(user.email)


def install_recording_email_sender() -> RecordingEmailSender:
    sender = RecordingEmailSender()
    app.dependency_overrides[get_password_reset_email_sender] = lambda: sender
    return sender


def test_signup_creates_hashed_user_and_sets_http_only_cookie(client, db_session):
    response = client.post("/api/v1/auth/signup", json=SIGNUP_PAYLOAD)

    assert response.status_code == 201
    assert response.json()["user"]["email"] == "driver.engineer@example.com"
    assert response.json()["user"]["username"] == "driverengineer"
    assert "access_token" not in response.json()
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=lax" in response.headers["set-cookie"]

    user = db_session.query(User).one()
    assert user.password_hash != SIGNUP_PAYLOAD["password"]
    assert SecurityService.verify_password(
        SIGNUP_PAYLOAD["password"], user.password_hash
    )


def test_signup_rejects_duplicate_email_or_username(client):
    assert client.post("/api/v1/auth/signup", json=SIGNUP_PAYLOAD).status_code == 201

    duplicate_email = {**SIGNUP_PAYLOAD, "username": "another-user"}
    duplicate_username = {
        **SIGNUP_PAYLOAD,
        "email": "another@example.com",
    }

    email_response = client.post("/api/v1/auth/signup", json=duplicate_email)
    username_response = client.post("/api/v1/auth/signup", json=duplicate_username)

    assert email_response.status_code == 409
    assert username_response.status_code == 409
    assert "email or username" in email_response.json()["detail"]


def test_login_accepts_email_or_username_and_me_returns_user(client):
    client.post("/api/v1/auth/signup", json=SIGNUP_PAYLOAD)
    client.post("/api/v1/auth/logout")

    email_login = client.post(
        "/api/v1/auth/login",
        json={
            "identifier": SIGNUP_PAYLOAD["email"],
            "password": SIGNUP_PAYLOAD["password"],
        },
    )
    assert email_login.status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 200

    client.post("/api/v1/auth/logout")
    username_login = client.post(
        "/api/v1/auth/login",
        json={
            "identifier": SIGNUP_PAYLOAD["username"],
            "password": SIGNUP_PAYLOAD["password"],
            "remember_me": True,
        },
    )
    assert username_login.status_code == 200
    assert "Max-Age" in username_login.headers["set-cookie"]


def test_login_uses_same_error_for_unknown_user_and_wrong_password(client):
    client.post("/api/v1/auth/signup", json=SIGNUP_PAYLOAD)
    client.post("/api/v1/auth/logout")

    unknown = client.post(
        "/api/v1/auth/login",
        json={"identifier": "unknown@example.com", "password": "wrong"},
    )
    wrong_password = client.post(
        "/api/v1/auth/login",
        json={"identifier": SIGNUP_PAYLOAD["email"], "password": "wrong"},
    )

    assert unknown.status_code == 401
    assert wrong_password.status_code == 401
    assert unknown.json() == wrong_password.json()


def test_login_rate_limit_blocks_repeated_failures(client):
    payload = {"identifier": "unknown@example.com", "password": "wrong"}

    for _ in range(settings.auth_login_max_attempts):
        assert client.post("/api/v1/auth/login", json=payload).status_code == 401

    response = client.post("/api/v1/auth/login", json=payload)

    assert response.status_code == 429
    assert int(response.headers["retry-after"]) >= 1


def test_protected_route_rejects_missing_invalid_and_expired_tokens(client):
    assert client.get("/api/v1/auth/me").status_code == 401

    client.cookies.set(settings.auth_cookie_name, "not-a-jwt")
    assert client.get("/api/v1/auth/me").status_code == 401

    client.cookies.clear()
    signup = client.post("/api/v1/auth/signup", json=SIGNUP_PAYLOAD)
    user_id = signup.json()["user"]["user_id"]
    expired = SecurityService.create_access_token(
        user_id,
        timedelta(seconds=-1),
    )
    client.cookies.clear()
    client.cookies.set(settings.auth_cookie_name, expired)
    assert client.get("/api/v1/auth/me").status_code == 401


def test_logout_clears_authentication_cookie(client):
    client.post("/api/v1/auth/signup", json=SIGNUP_PAYLOAD)
    assert client.get("/api/v1/auth/me").status_code == 200

    response = client.post("/api/v1/auth/logout")

    assert response.status_code == 204
    assert client.get("/api/v1/auth/me").status_code == 401


def test_forgot_password_has_identical_response_for_existing_and_unknown_accounts(
    client,
):
    client.post("/api/v1/auth/signup", json=SIGNUP_PAYLOAD)
    sender = install_recording_email_sender()

    existing = client.post(
        "/api/v1/auth/forgot-password",
        json={"identifier": SIGNUP_PAYLOAD["email"]},
    )
    unknown = client.post(
        "/api/v1/auth/forgot-password",
        json={"identifier": "unknown@example.com"},
    )

    assert existing.status_code == 202
    assert unknown.status_code == 202
    assert existing.json() == unknown.json()
    assert "If an account matches" in existing.json()["message"]
    assert len(sender.reset_emails) == 1


def test_password_reset_token_is_hashed_and_verifiable(client, db_session):
    client.post("/api/v1/auth/signup", json=SIGNUP_PAYLOAD)
    sender = install_recording_email_sender()
    client.post(
        "/api/v1/auth/forgot-password",
        json={"identifier": SIGNUP_PAYLOAD["username"]},
    )
    plaintext_token = sender.reset_emails[0][1]

    stored = db_session.query(PasswordResetToken).one()
    assert stored.token_hash != plaintext_token
    assert stored.token_hash == SecurityService.hash_password_reset_token(
        plaintext_token
    )
    verify = client.get(
        "/api/v1/auth/reset-password/verify",
        params={"token": plaintext_token},
    )
    assert verify.status_code == 200
    assert verify.json()["valid"] is True


def test_password_reset_is_single_use_and_invalidates_existing_sessions(
    client,
    db_session,
):
    client.post("/api/v1/auth/signup", json=SIGNUP_PAYLOAD)
    old_access_token = client.cookies.get(settings.auth_cookie_name)
    sender = install_recording_email_sender()
    client.post(
        "/api/v1/auth/forgot-password",
        json={"identifier": SIGNUP_PAYLOAD["email"]},
    )
    reset_token = sender.reset_emails[0][1]
    new_password = "ResetSecure!456"

    response = client.post(
        "/api/v1/auth/reset-password",
        json={"token": reset_token, "new_password": new_password},
    )

    assert response.status_code == 204
    user = db_session.query(User).one()
    assert user.token_version == 1
    assert SecurityService.verify_password(new_password, user.password_hash)
    assert sender.changed_emails == ["driver.engineer@example.com"]

    client.cookies.clear()
    invalidated = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {old_access_token}"},
    )
    assert invalidated.status_code == 401

    reused = client.post(
        "/api/v1/auth/reset-password",
        json={"token": reset_token, "new_password": "AnotherReset!789"},
    )
    assert reused.status_code == 400
    assert "already been used" in reused.json()["detail"]

    login = client.post(
        "/api/v1/auth/login",
        json={"identifier": SIGNUP_PAYLOAD["email"], "password": new_password},
    )
    assert login.status_code == 200


def test_expired_password_reset_token_returns_clear_error(client, db_session):
    client.post("/api/v1/auth/signup", json=SIGNUP_PAYLOAD)
    sender = install_recording_email_sender()
    client.post(
        "/api/v1/auth/forgot-password",
        json={"identifier": SIGNUP_PAYLOAD["email"]},
    )
    reset_token = sender.reset_emails[0][1]
    stored = db_session.query(PasswordResetToken).one()
    stored.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db_session.commit()

    response = client.get(
        "/api/v1/auth/reset-password/verify",
        params={"token": reset_token},
    )

    assert response.status_code == 400
    assert "expired" in response.json()["detail"]


def test_new_reset_request_invalidates_the_previous_token(client):
    client.post("/api/v1/auth/signup", json=SIGNUP_PAYLOAD)
    sender = install_recording_email_sender()

    for _ in range(2):
        assert client.post(
            "/api/v1/auth/forgot-password",
            json={"identifier": SIGNUP_PAYLOAD["email"]},
        ).status_code == 202

    first_token = sender.reset_emails[0][1]
    second_token = sender.reset_emails[1][1]
    first = client.get(
        "/api/v1/auth/reset-password/verify",
        params={"token": first_token},
    )
    second = client.get(
        "/api/v1/auth/reset-password/verify",
        params={"token": second_token},
    )

    assert first.status_code == 400
    assert "superseded by a newer request" in first.json()["detail"]
    assert second.status_code == 200


def test_password_reset_enforces_password_policy_and_rate_limit(client):
    sender = install_recording_email_sender()
    client.post("/api/v1/auth/signup", json=SIGNUP_PAYLOAD)
    client.post(
        "/api/v1/auth/forgot-password",
        json={"identifier": SIGNUP_PAYLOAD["email"]},
    )
    reset_token = sender.reset_emails[0][1]

    weak = client.post(
        "/api/v1/auth/reset-password",
        json={"token": reset_token, "new_password": "weak"},
    )
    assert weak.status_code == 422

    # The first request above counts toward the per-IP and per-identifier limit.
    for _ in range(settings.password_reset_max_requests - 1):
        assert client.post(
            "/api/v1/auth/forgot-password",
            json={"identifier": SIGNUP_PAYLOAD["email"]},
        ).status_code == 202

    limited = client.post(
        "/api/v1/auth/forgot-password",
        json={"identifier": SIGNUP_PAYLOAD["email"]},
    )
    assert limited.status_code == 429
    assert int(limited.headers["retry-after"]) >= 1
