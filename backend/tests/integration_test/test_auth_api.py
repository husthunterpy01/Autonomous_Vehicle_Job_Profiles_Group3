from datetime import timedelta

from app.core.config import settings
from app.models.user import User
from app.utils.security import SecurityService

SIGNUP_PAYLOAD = {
    "email": "Driver.Engineer@example.com",
    "username": "DriverEngineer",
    "full_name": "Driver Engineer",
    "password": "SecurePassword!123",
}


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
