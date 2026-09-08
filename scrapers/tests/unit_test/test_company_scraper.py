from scrapers.utils.company_scraper import CompanyScraper


def test_enabled_html_and_xml_sources_split_by_ats():
    companies = [
        {"key": "tensor", "name": "Tensor", "ats": "html", "enabled": True},
        {"key": "momenta", "name": "Momenta", "ats": "xml", "enabled": True},
        {"key": "old", "name": "Old", "ats": "xml", "enabled": False},
        {"key": "stack_av", "name": "Stack AV", "ats": "greenhouse", "slug": "s", "enabled": True},
    ]

    assert [c["key"] for c in CompanyScraper.enabled_html_sources(companies)] == ["tensor"]
    assert [c["key"] for c in CompanyScraper.enabled_xml_sources(companies)] == ["momenta"]
    assert (
        [c["key"] for c in CompanyScraper.enabled_xml_sources(companies, company_key="momenta")]
        == ["momenta"]
    )


def test_real_yaml_has_momenta_as_enabled_xml_source():
    companies = CompanyScraper.load_company_list()
    xml_keys = [c["key"] for c in CompanyScraper.enabled_xml_sources(companies)]
    assert "momenta" in xml_keys


def test_scrape_company_does_not_skip_xml_without_slug():
    from unittest.mock import patch

    with patch("scrapers.utils.company_scraper.RawFetch") as mock_fetch:
        mock_fetch.from_company.return_value = (mock_fetch.return_value, "https://feed/xml")
        mock_fetch.return_value.fetch_and_archive.return_value = "xml/momenta/f.parquet"
        count = CompanyScraper.scrape_company(
            {"name": "Momenta", "ats": "xml", "slug": None, "url": "https://feed/xml"}, timeout=5
        )

    assert count == 1
    mock_fetch.from_company.assert_called_once()


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

    selected = CompanyScraper.enabled_api_sources(companies)

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

    selected = CompanyScraper.enabled_api_sources(companies, company_key="bosch")

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
    monkeypatch.setattr(CompanyScraper, "COMPANY_LIST_PATH", str(yaml_path))

    companies = CompanyScraper.load_company_list()

    assert companies[0]["key"] == "stack_av"


def test_load_company_list_rejects_invalid_yaml(tmp_path, monkeypatch):
    yaml_path = tmp_path / "list_companies.yaml"
    yaml_path.write_text("companies: not-a-list\n", encoding="utf-8")
    monkeypatch.setattr(CompanyScraper, "COMPANY_LIST_PATH", str(yaml_path))

    try:
        CompanyScraper.load_company_list()
    except ValueError as exc:
        assert "companies list" in str(exc)
    else:
        raise AssertionError("expected ValueError")
