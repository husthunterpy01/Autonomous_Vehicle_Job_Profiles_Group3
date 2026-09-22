ENDPOINT = "/api/v1/companies"


def _new_company_payload(**overrides):
    payload = {
        "name": "New Robotics Co",
        "website_url": "https://new-robotics.example.com",
        "career_page_url": "https://new-robotics.example.com/careers",
        "company_type": "AV_Startup",
        "datasource_status": "confirmed",
    }
    payload.update(overrides)
    return payload


def test_list_companies_returns_all_ordered_by_name(client, seeded_companies):
    response = client.get(ENDPOINT)

    assert response.status_code == 200
    body = response.json()
    assert [company["name"] for company in body] == ["Alpha Robotics", "Beta AV", "Gamma Drive"]
    assert set(body[0].keys()) == {
        "company_id",
        "name",
        "company_type",
        "website_url",
        "career_page_url",
        "datasource_status",
    }


def test_get_company_by_id_returns_the_company(client, seeded_companies):
    alpha = seeded_companies["alpha"]

    response = client.get(f"{ENDPOINT}/{alpha.company_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["company_id"] == str(alpha.company_id)
    assert body["name"] == "Alpha Robotics"


def test_get_company_by_id_returns_404_for_unknown_id(client):
    response = client.get(f"{ENDPOINT}/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404


def test_create_company_succeeds(client):
    response = client.post(ENDPOINT, json=_new_company_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "New Robotics Co"
    assert body["website_url"] == "https://new-robotics.example.com"

    # It's actually persisted and independently retrievable.
    follow_up = client.get(f"{ENDPOINT}/{body['company_id']}")
    assert follow_up.status_code == 200
    assert follow_up.json()["name"] == "New Robotics Co"


def test_create_company_conflicts_on_duplicate_name(client):
    assert client.post(ENDPOINT, json=_new_company_payload()).status_code == 201

    response = client.post(
        ENDPOINT,
        json=_new_company_payload(
            website_url="https://different.example.com",
            career_page_url="https://different.example.com/careers",
        ),
    )

    assert response.status_code == 409


def test_create_company_conflicts_on_duplicate_website_url(client):
    assert client.post(ENDPOINT, json=_new_company_payload()).status_code == 201

    response = client.post(
        ENDPOINT,
        json=_new_company_payload(
            name="Different Co",
            career_page_url="https://different.example.com/careers",
        ),
    )

    assert response.status_code == 409


def test_create_company_conflicts_on_duplicate_career_page_url(client):
    assert client.post(ENDPOINT, json=_new_company_payload()).status_code == 201

    response = client.post(
        ENDPOINT,
        json=_new_company_payload(
            name="Different Co",
            website_url="https://different.example.com",
        ),
    )

    assert response.status_code == 409


def test_create_company_rejects_blank_required_fields(client):
    response = client.post(ENDPOINT, json=_new_company_payload(name="   "))

    assert response.status_code == 422
