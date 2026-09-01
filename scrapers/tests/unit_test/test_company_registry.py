from scrapers.utils.company_registry import CompanyRegistry


def test_enabled_api_sources_skips_disabled_and_non_api_rows():
    companies = [
        {"key": "waabi", "name": "Waabi", "ats": "lever", "slug": "waabi", "enabled": False},
        {"key": "waymo", "name": "Waymo", "ats": "html", "slug": "waymo", "enabled": True},
        {
            "key": "stack_av",
            "name": "Stack AV",
            "ats": "greenhouse",
            "slug": "stackav",
            "enabled": True,
        },
    ]

    selected = CompanyRegistry.enabled_api_sources(companies)

    assert [row["key"] for row in selected] == ["stack_av"]


def test_enabled_api_sources_filters_by_company_key():
    companies = [
        {
            "key": "stack_av",
            "name": "Stack AV",
            "ats": "greenhouse",
            "slug": "stackav",
            "enabled": True,
        },
        {
            "key": "bosch",
            "name": "Bosch",
            "ats": "smartrecruiters",
            "slug": "BoschGroup",
            "enabled": True,
        },
    ]

    selected = CompanyRegistry.enabled_api_sources(companies, company_key="bosch")

    assert [row["key"] for row in selected] == ["bosch"]


def test_load_company_list_reads_yaml(tmp_path, monkeypatch):
    yaml_path = tmp_path / "list_companies.yaml"
    yaml_path.write_text(
        "companies:\n"
        "  - key: stack_av\n"
        "    name: Stack AV\n"
        "    ats: greenhouse\n"
        "    slug: stackav\n"
        "    enabled: true\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(CompanyRegistry, "COMPANY_LIST_PATH", str(yaml_path))

    companies = CompanyRegistry.load_company_list()

    assert companies[0]["key"] == "stack_av"


def test_load_company_list_rejects_invalid_yaml(tmp_path, monkeypatch):
    yaml_path = tmp_path / "list_companies.yaml"
    yaml_path.write_text("companies: not-a-list\n", encoding="utf-8")
    monkeypatch.setattr(CompanyRegistry, "COMPANY_LIST_PATH", str(yaml_path))

    try:
        CompanyRegistry.load_company_list()
    except ValueError as exc:
        assert "companies list" in str(exc)
    else:
        raise AssertionError("expected ValueError")
