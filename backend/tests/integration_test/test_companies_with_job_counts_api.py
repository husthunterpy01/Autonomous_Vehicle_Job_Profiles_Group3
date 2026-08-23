ENDPOINT = "/api/v1/companies/with-job-counts"


def test_with_job_counts_default_pagination(client):
    response = client.get(ENDPOINT)

    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 1
    assert body["page_size"] == 10
    assert body["total"] == 3
    assert body["total_pages"] == 1
    assert len(body["items"]) == 3


def test_with_job_counts_explicit_pagination(client):
    response = client.get(ENDPOINT, params={"page": 1, "page_size": 10})

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {
        "items",
        "total",
        "page",
        "page_size",
        "total_pages",
    }
    assert body["page"] == 1
    assert body["page_size"] == 10
    assert body["total"] == 3
    assert body["total_pages"] == 1
    assert len(body["items"]) == 3

    first = body["items"][0]
    assert set(first.keys()) == {
        "company_id",
        "name",
        "company_type",
        "location",
        "number_of_jobs",
    }
    assert first["name"] == "Alpha Robotics"
    assert first["location"] == "United States"
    assert first["number_of_jobs"] == 2


def test_with_job_counts_invalid_page_returns_422(client):
    for page in (0, -1, "abc"):
        response = client.get(ENDPOINT, params={"page": page, "page_size": 10})
        assert response.status_code == 422, page


def test_with_job_counts_invalid_page_size_returns_422(client):
    for page_size in (0, -1, 101, "abc"):
        response = client.get(ENDPOINT, params={"page": 1, "page_size": page_size})
        assert response.status_code == 422, page_size


def test_with_job_counts_page_beyond_last_returns_empty_items(client):
    response = client.get(ENDPOINT, params={"page": 5, "page_size": 10})

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 3
    assert body["page"] == 5
    assert body["page_size"] == 10
    assert body["total_pages"] == 1
