"""Covers CompanyService.add_new_company's error-handling branches that the
three explicit pre-checks (duplicate name/website/career_page, each a plain
SELECT before any write) can never reach on their own: a genuine DB-level
integrity violation or unexpected error surfacing from db.commit() itself
(e.g. a race between the pre-check and the write)."""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.schemas.company import CompanyCreate
from app.services.company import CompanyService


def _db_with_no_conflicts():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    return db


def _company_create():
    return CompanyCreate(
        name="New Robotics Co",
        website_url="https://new-robotics.example.com",
        career_page_url="https://new-robotics.example.com/careers",
        company_type="AV_Startup",
        datasource_status="confirmed",
    )


def test_add_new_company_converts_integrity_error_on_commit_to_409():
    db = _db_with_no_conflicts()
    db.commit.side_effect = IntegrityError("INSERT", {}, Exception("duplicate key"))

    with pytest.raises(HTTPException) as raised:
        CompanyService.add_new_company(db, _company_create())

    assert raised.value.status_code == 409
    db.rollback.assert_called_once()


def test_add_new_company_rolls_back_and_reraises_unexpected_errors():
    db = _db_with_no_conflicts()
    db.commit.side_effect = RuntimeError("connection reset")

    with pytest.raises(RuntimeError, match="connection reset"):
        CompanyService.add_new_company(db, _company_create())

    db.rollback.assert_called_once()
