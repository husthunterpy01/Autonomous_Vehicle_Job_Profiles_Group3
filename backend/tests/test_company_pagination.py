from app.services.company import CompanyService
from tests.conftest import make_company, seed_companies_with_jobs


def test_get_companies_with_num_jobs_returns_first_page(db_session):
    seed_companies_with_jobs(db_session)

    result = CompanyService.get_companies_with_num_jobs(
        db_session,
        page=1,
        page_size=2,
    )

    assert result.total == 3
    assert result.page == 1
    assert result.page_size == 2
    assert result.total_pages == 2
    assert len(result.items) == 2
    assert [item.name for item in result.items] == ["Alpha Robotics", "Beta AV"]


def test_get_companies_with_num_jobs_returns_second_page(db_session):
    seed_companies_with_jobs(db_session)

    result = CompanyService.get_companies_with_num_jobs(
        db_session,
        page=2,
        page_size=2,
    )

    assert len(result.items) == 1
    assert result.items[0].name == "Gamma Drive"


def test_get_companies_with_num_jobs_includes_job_counts(db_session):
    companies = seed_companies_with_jobs(db_session)

    result = CompanyService.get_companies_with_num_jobs(
        db_session,
        page=1,
        page_size=10,
    )

    by_name = {item.name: item.number_of_jobs for item in result.items}

    assert by_name["Alpha Robotics"] == 2
    assert by_name["Beta AV"] == 1
    assert by_name["Gamma Drive"] == 0
    assert companies["alpha"].company_id in {item.company_id for item in result.items}


def test_get_companies_with_num_jobs_includes_location_or_none(db_session):
    seed_companies_with_jobs(db_session)

    result = CompanyService.get_companies_with_num_jobs(
        db_session,
        page=1,
        page_size=10,
    )

    by_name = {item.name: item.location for item in result.items}

    assert by_name["Alpha Robotics"] == "United States"
    assert by_name["Beta AV"] == "Canada"
    assert by_name["Gamma Drive"] is None


def test_get_companies_with_num_jobs_orders_by_company_name(db_session):
    zebra = make_company("Zebra Mobility")
    acme = make_company("Acme Autonomy")
    db_session.add_all([zebra, acme])
    db_session.commit()

    result = CompanyService.get_companies_with_num_jobs(
        db_session,
        page=1,
        page_size=10,
    )

    assert [item.name for item in result.items] == ["Acme Autonomy", "Zebra Mobility"]
