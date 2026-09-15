from app.models import JobPosting

SIGNUP_PAYLOAD = {
    "email": "Driver.Engineer@example.com",
    "username": "DriverEngineer",
    "full_name": "Driver Engineer",
    "password": "SecurePassword!123",
}


def _signup(client):
    return client.post("/api/v1/auth/signup", json=SIGNUP_PAYLOAD)


def test_favorites_require_authentication(client):
    assert client.get("/api/v1/favorites").status_code == 401


def test_list_favorites_empty_by_default(client):
    _signup(client)
    response = client.get("/api/v1/favorites")
    assert response.status_code == 200
    assert response.json() == []


def test_add_list_and_remove_favorite(client, db_session, seeded_companies):
    _signup(client)
    job = db_session.query(JobPosting).first()

    add_response = client.post(f"/api/v1/favorites/{job.job_id}")
    assert add_response.status_code == 204

    list_response = client.get("/api/v1/favorites")
    assert list_response.status_code == 200
    job_ids = [item["job_id"] for item in list_response.json()]
    assert job_ids == [str(job.job_id)]

    # Adding the same job twice is idempotent, not a duplicate.
    assert client.post(f"/api/v1/favorites/{job.job_id}").status_code == 204
    assert len(client.get("/api/v1/favorites").json()) == 1

    remove_response = client.delete(f"/api/v1/favorites/{job.job_id}")
    assert remove_response.status_code == 204
    assert client.get("/api/v1/favorites").json() == []

    # Removing an already-removed favorite is also idempotent.
    assert client.delete(f"/api/v1/favorites/{job.job_id}").status_code == 204


def test_add_favorite_rejects_unknown_job(client):
    _signup(client)
    response = client.post(
        "/api/v1/favorites/00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 404


def test_favorites_are_scoped_per_user(client, db_session, seeded_companies):
    job = db_session.query(JobPosting).first()
    _signup(client)
    client.post(f"/api/v1/favorites/{job.job_id}")
    client.post("/api/v1/auth/logout")

    other_user = {
        **SIGNUP_PAYLOAD,
        "email": "other@example.com",
        "username": "otheruser",
    }
    client.post("/api/v1/auth/signup", json=other_user)

    assert client.get("/api/v1/favorites").json() == []
