from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event, text
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.models import FavoriteCompany, FavoriteJob, JobPosting, User
from app.services.favorite import FavoriteService
from app.utils.security import SecurityService


def sign_up(client, *, suffix: str = "one") -> UUID:
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": f"favorite-{suffix}@example.com",
            "username": f"favorite_{suffix}",
            "full_name": f"Favorite User {suffix}",
            "password": "SecurePassword!123",
        },
    )
    assert response.status_code == 201
    return UUID(response.json()["user"]["user_id"])


def test_job_favorite_add_list_duplicate_and_remove(client, db_session):
    user_id = sign_up(client)
    job = db_session.query(JobPosting).filter_by(name="alpha-job-1").one()
    path = f"/api/v1/favorites/jobs/{job.job_id}"

    added = client.post(path)
    assert added.status_code == 201
    assert added.json()["job_id"] == str(job.job_id)
    assert added.json()["job"]["title"] == job.title
    assert added.json()["job"]["company_name"] == "Alpha Robotics"
    assert added.json()["created_at"]
    assert db_session.query(FavoriteJob).filter_by(user_id=user_id).count() == 1

    duplicate = client.post(path)
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "Job already favorited"
    assert db_session.query(FavoriteJob).filter_by(user_id=user_id).count() == 1

    job.title = "Updated AV Engineer"
    db_session.commit()
    listed = client.get("/api/v1/favorites/jobs")
    assert listed.status_code == 200
    assert [item["job_id"] for item in listed.json()] == [str(job.job_id)]
    assert listed.json()[0]["job"]["title"] == "Updated AV Engineer"

    assert client.delete(path).status_code == 204
    assert client.get("/api/v1/favorites/jobs").json() == []
    assert client.delete(path).status_code == 404


def test_company_favorite_add_list_duplicate_and_remove(client, db_session, seeded_companies):
    user_id = sign_up(client)
    company = seeded_companies["gamma"]
    path = f"/api/v1/favorites/companies/{company.company_id}"

    added = client.post(path)
    assert added.status_code == 201
    assert added.json()["company_id"] == str(company.company_id)
    assert added.json()["company"]["name"] == "Gamma Drive"
    assert db_session.query(FavoriteCompany).filter_by(user_id=user_id).count() == 1
    assert client.post(path).status_code == 409
    assert db_session.query(FavoriteCompany).filter_by(user_id=user_id).count() == 1

    company.name = "Gamma Mobility"
    db_session.commit()
    listed = client.get("/api/v1/favorites/companies")
    assert listed.status_code == 200
    assert listed.json()[0]["company"]["name"] == "Gamma Mobility"

    assert client.delete(path).status_code == 204
    assert client.get("/api/v1/favorites/companies").json() == []
    assert client.delete(path).status_code == 404


def test_favorites_are_isolated_by_authenticated_user(client, db_session, seeded_companies):
    first_user = sign_up(client, suffix="first")
    job = db_session.query(JobPosting).filter_by(name="beta-job-1").one()
    company = seeded_companies["gamma"]
    job_path = f"/api/v1/favorites/jobs/{job.job_id}"
    company_path = f"/api/v1/favorites/companies/{company.company_id}"
    assert client.post(job_path).status_code == 201
    assert client.post(company_path).status_code == 201

    second_user = sign_up(client, suffix="second")
    assert client.get("/api/v1/favorites/jobs").json() == []
    assert client.get("/api/v1/favorites/companies").json() == []
    assert client.delete(job_path).status_code == 404
    assert client.delete(company_path).status_code == 404
    assert client.post(job_path).status_code == 201

    assert db_session.query(FavoriteJob).filter_by(user_id=first_user).count() == 1
    assert db_session.query(FavoriteJob).filter_by(user_id=second_user).count() == 1
    assert db_session.query(FavoriteCompany).filter_by(user_id=first_user).count() == 1
    assert db_session.query(FavoriteCompany).filter_by(user_id=second_user).count() == 0

    client.cookies.clear()
    first_token = SecurityService.create_access_token(first_user, timedelta(minutes=5))
    headers = {"Authorization": f"Bearer {first_token}"}
    assert len(client.get("/api/v1/favorites/jobs", headers=headers).json()) == 1
    assert len(client.get("/api/v1/favorites/companies", headers=headers).json()) == 1


def test_favorites_reject_missing_targets_and_unauthenticated_requests(client, db_session):
    missing_id = uuid4()
    job_path = f"/api/v1/favorites/jobs/{missing_id}"
    company_path = f"/api/v1/favorites/companies/{missing_id}"

    for method, path in (
        (client.get, "/api/v1/favorites/jobs"),
        (client.get, "/api/v1/favorites/companies"),
        (client.post, job_path),
        (client.post, company_path),
        (client.delete, job_path),
        (client.delete, company_path),
    ):
        assert method(path).status_code == 401

    sign_up(client)
    assert client.post(job_path).status_code == 404
    assert client.post(company_path).status_code == 404
    assert client.delete(job_path).status_code == 404
    assert client.delete(company_path).status_code == 404
    assert client.post("/api/v1/favorites/jobs/not-a-uuid").status_code == 422
    assert db_session.query(FavoriteJob).count() == 0
    assert db_session.query(FavoriteCompany).count() == 0

    client.cookies.clear()
    client.cookies.set(settings.auth_cookie_name, "invalid-token")
    assert client.get("/api/v1/favorites/jobs").status_code == 401


def test_inactive_user_cannot_access_favorites(client, db_session):
    user_id = sign_up(client)
    user = db_session.get(User, user_id)
    user.is_active = False
    db_session.commit()
    assert client.get("/api/v1/favorites/jobs").status_code == 401
    assert client.get("/api/v1/favorites/companies").status_code == 401


def test_deleted_targets_are_cascaded_out_of_favorites(client, db_session, seeded_companies):
    user_id = sign_up(client)
    job = db_session.query(JobPosting).filter_by(name="alpha-job-1").one()
    company = seeded_companies["gamma"]  # No jobs reference this company.
    assert client.post(f"/api/v1/favorites/jobs/{job.job_id}").status_code == 201
    assert client.post(f"/api/v1/favorites/companies/{company.company_id}").status_code == 201

    db_session.execute(text("PRAGMA foreign_keys = ON"))
    db_session.delete(job)
    db_session.delete(company)
    db_session.commit()
    db_session.expire_all()

    assert db_session.query(FavoriteJob).filter_by(user_id=user_id).count() == 0
    assert db_session.query(FavoriteCompany).filter_by(user_id=user_id).count() == 0
    assert client.get("/api/v1/favorites/jobs").json() == []
    assert client.get("/api/v1/favorites/companies").json() == []


def test_database_primary_keys_prevent_duplicate_favorites(client, db_session, seeded_companies):
    user_id = sign_up(client)
    job = db_session.query(JobPosting).filter_by(name="beta-job-1").one()
    company = seeded_companies["gamma"]
    assert client.post(f"/api/v1/favorites/jobs/{job.job_id}").status_code == 201
    assert client.post(f"/api/v1/favorites/companies/{company.company_id}").status_code == 201

    db_session.add(FavoriteJob(user_id=user_id, job_id=job.job_id))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    db_session.add(FavoriteCompany(user_id=user_id, company_id=company.company_id))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_favorite_job_list_uses_constant_number_of_queries(client, db_session):
    user_id = sign_up(client)
    jobs = db_session.query(JobPosting).order_by(JobPosting.name).all()
    assert len(jobs) >= 3

    def count_selects():
        selects = []

        def record_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
            if statement.lstrip().lower().startswith("select"):
                selects.append(statement)

        db_session.expire_all()
        event.listen(db_session.bind, "before_cursor_execute", record_sql)
        try:
            response = FavoriteService.list_jobs(db_session, user_id)
        finally:
            event.remove(db_session.bind, "before_cursor_execute", record_sql)
        return len(selects), response

    assert client.post(f"/api/v1/favorites/jobs/{jobs[0].job_id}").status_code == 201
    one_count, one_response = count_selects()
    for job in jobs[1:]:
        assert client.post(f"/api/v1/favorites/jobs/{job.job_id}").status_code == 201
    many_count, many_response = count_selects()

    assert len(one_response) == 1
    assert len(many_response) == len(jobs)
    assert many_count == one_count
