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


def test_authenticated_user_can_read_and_update_own_profile(client, db_session):
    client.post("/api/v1/auth/signup", json=SIGNUP_PAYLOAD)

    before = client.get("/api/v1/auth/me")
    assert before.status_code == 200
    assert before.json()["phone"] is None
    assert before.json()["address"] is None

    response = client.patch(
        "/api/v1/auth/me",
        json={
            "email": "Updated.Driver@example.com",
            "username": "Updated.Driver",
            "full_name": "  Updated   Driver  ",
            "phone": "+61 412 345 678",
            "address": "  Perth,   Western Australia  ",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "updated.driver@example.com"
    assert body["username"] == "updated.driver"
    assert body["full_name"] == "Updated Driver"
    assert body["phone"] == "+61 412 345 678"
    assert body["address"] == "Perth, Western Australia"
    user = db_session.query(User).one()
    assert user.email == "updated.driver@example.com"
    assert user.phone == "+61 412 345 678"


def test_profile_update_requires_authentication_and_valid_fields(client):
    unauthorized = client.patch("/api/v1/auth/me", json={"full_name": "Other"})
    assert unauthorized.status_code == 401

    client.post("/api/v1/auth/signup", json=SIGNUP_PAYLOAD)
    assert client.patch("/api/v1/auth/me", json={}).status_code == 422
    assert client.patch("/api/v1/auth/me", json={"email": None}).status_code == 422
    assert client.patch("/api/v1/auth/me", json={"phone": "letters"}).status_code == 422


def test_profile_update_rejects_another_users_email_or_username(client):
    client.post("/api/v1/auth/signup", json=SIGNUP_PAYLOAD)
    client.post("/api/v1/auth/logout")
    second_user = {
        "email": "second@example.com",
        "username": "second-user",
        "full_name": "Second User",
        "password": "AnotherSecure!123",
    }
    client.post("/api/v1/auth/signup", json=second_user)

    duplicate_email = client.patch(
        "/api/v1/auth/me", json={"email": SIGNUP_PAYLOAD["email"]}
    )
    duplicate_username = client.patch(
        "/api/v1/auth/me", json={"username": SIGNUP_PAYLOAD["username"]}
    )

    assert duplicate_email.status_code == 409
    assert duplicate_username.status_code == 409


def test_password_change_requires_current_password_and_rejects_reuse(client, db_session):
    client.post("/api/v1/auth/signup", json=SIGNUP_PAYLOAD)

    incorrect = client.patch(
        "/api/v1/auth/me/password",
        json={"current_password": "Incorrect!123", "new_password": "NewPassword!123"},
    )
    reused = client.patch(
        "/api/v1/auth/me/password",
        json={
            "current_password": SIGNUP_PAYLOAD["password"],
            "new_password": SIGNUP_PAYLOAD["password"],
        },
    )

    assert incorrect.status_code == 400
    assert incorrect.json()["detail"] == "Current password is incorrect"
    assert reused.status_code == 400
    assert "different" in reused.json()["detail"]
    user = db_session.query(User).one()
    assert SecurityService.verify_password(
        SIGNUP_PAYLOAD["password"], user.password_hash
    )


def test_password_change_rehashes_password_and_never_returns_it(client, db_session):
    client.post("/api/v1/auth/signup", json=SIGNUP_PAYLOAD)
    new_password = "UpdatedSecure!456"

    response = client.patch(
        "/api/v1/auth/me/password",
        json={
            "current_password": SIGNUP_PAYLOAD["password"],
            "new_password": new_password,
        },
    )

    assert response.status_code == 204
    assert response.content == b""
    user = db_session.query(User).one()
    assert new_password not in user.password_hash
    assert SecurityService.verify_password(new_password, user.password_hash)

    client.post("/api/v1/auth/logout")
    assert client.post(
        "/api/v1/auth/login",
        json={"identifier": SIGNUP_PAYLOAD["email"], "password": new_password},
    ).status_code == 200
