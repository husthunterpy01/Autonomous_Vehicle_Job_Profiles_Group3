import json
import logging

import pytest
import yaml
from scrapers.utils.build_classification_handoff import (
    DEFAULT_MAIN_TYPES_PATH,
    _load_main_types,
    build_handoff_records,
    main,
)


def _write_jsonl(path, rows):
    with path.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row) + "\n")


def _build(paths, **kwargs):
    kwargs.setdefault("main_types_path", None)
    kwargs.setdefault("company_salary_cache_path", None)
    return build_handoff_records(paths, **kwargs)


def test_reshapes_categories_into_functional_area_strings(tmp_path):
    path = tmp_path / "av_jobs.jsonl"
    _write_jsonl(
        path,
        [
            {
                "deduplication_key": "a",
                "_classification": {
                    "categories": ["Perception"],
                    "skills": [{"name": "ROS 2", "skill_type": "framework"}],
                },
            }
        ],
    )

    records = _build([path])

    assert records == [
        {
            "deduplication_key": "a",
            "functional_area": ["Perception"],
            "skills": [{"name": "ROS 2", "skill_type": "framework"}],
        }
    ]


def test_functional_area_never_carries_main_type_even_when_mapping_is_known(tmp_path):
    # main_type is a property of the category, owned by the backend's own
    # copy of category_main_types.yaml - a per-record main_type would let two
    # disagreeing records silently flip a shared Category row.
    path = tmp_path / "av_jobs.jsonl"
    _write_jsonl(
        path,
        [{"deduplication_key": "a", "_classification": {"categories": ["Perception", "Sensing"], "skills": []}}],
    )
    main_types_path = tmp_path / "category_main_types.yaml"
    main_types_path.write_text(yaml.safe_dump({"Perception": "Perception & Sensing", "Sensing": "Perception & Sensing"}))

    records = _build([path], main_types_path=main_types_path)

    assert records[0]["functional_area"] == ["Perception", "Sensing"]


def test_warns_on_unmapped_category(tmp_path, caplog):
    path = tmp_path / "av_jobs.jsonl"
    _write_jsonl(
        path,
        [{"deduplication_key": "a", "_classification": {"categories": ["Perception"], "skills": []}}],
    )
    main_types_path = tmp_path / "category_main_types.yaml"
    main_types_path.write_text(yaml.safe_dump({"Sensing": "Perception & Sensing"}))

    with caplog.at_level(logging.WARNING):
        records = _build([path], main_types_path=main_types_path)

    assert records[0]["functional_area"] == ["Perception"]
    assert "Perception" in caplog.text


def test_default_main_types_path_is_module_relative_not_cwd_relative(monkeypatch, tmp_path):
    # Regression test: the old `Path("scrapers") / "config" / ...` default
    # only resolved when the process happened to be launched from the repo
    # root. Simulate running from an unrelated cwd (e.g. backend/) and
    # confirm the default still finds the real, checked-in mapping file.
    monkeypatch.chdir(tmp_path)
    assert DEFAULT_MAIN_TYPES_PATH.is_file()
    mapping = _load_main_types(DEFAULT_MAIN_TYPES_PATH)
    assert mapping.get("Perception") == "Perception & Sensing"


def test_missing_default_main_types_path_fails_loudly(monkeypatch, tmp_path):
    # A missing *default* path is a real problem (bad cwd assumption gone
    # wrong again, a moved/renamed file), not an intentional opt-out - it
    # must raise, not silently return {} and let every category come back
    # unmapped with exit 0.
    broken_default = tmp_path / "does_not_exist.yaml"
    monkeypatch.setattr("scrapers.utils.build_classification_handoff.DEFAULT_MAIN_TYPES_PATH", broken_default)

    with pytest.raises(FileNotFoundError, match="Default category main-types file"):
        _load_main_types(broken_default)


def test_explicit_missing_main_types_path_still_skips_silently(tmp_path):
    # An explicitly-passed missing path is the documented way to opt out
    # (see --main-types --help); only the *default* failing loudly changes.
    explicit_missing_path = tmp_path / "does_not_exist.yaml"
    assert explicit_missing_path != DEFAULT_MAIN_TYPES_PATH
    assert _load_main_types(explicit_missing_path) == {}


def test_skips_rows_with_no_categories(tmp_path):
    path = tmp_path / "av_jobs.jsonl"
    _write_jsonl(
        path,
        [
            {"deduplication_key": "a", "_classification": {"categories": [], "skills": []}},
            {"deduplication_key": "b", "_classification": {}},
        ],
    )

    assert _build([path]) == []


def test_later_file_overrides_earlier_on_duplicate_key(tmp_path):
    keyword_path = tmp_path / "keyword_resolved.jsonl"
    llm_path = tmp_path / "av_jobs.jsonl"
    _write_jsonl(
        keyword_path,
        [{"deduplication_key": "a", "_classification": {"categories": ["Sensing"], "skills": []}}],
    )
    _write_jsonl(
        llm_path,
        [{"deduplication_key": "a", "_classification": {"categories": ["Perception"], "skills": []}}],
    )

    records = _build([keyword_path, llm_path])

    assert len(records) == 1
    assert records[0]["functional_area"] == ["Perception"]


def test_main_writes_json_array_to_output(tmp_path):
    input_path = tmp_path / "av_jobs.jsonl"
    output_path = tmp_path / "handoff.json"
    _write_jsonl(
        input_path,
        [{"deduplication_key": "a", "_classification": {"categories": ["Planning"], "skills": []}}],
    )

    status = main(
        [
            "--input", str(input_path),
            "--output", str(output_path),
            "--main-types", str(tmp_path / "does_not_exist.yaml"),
            "--company-salary-cache", str(tmp_path / "does_not_exist_cache.yaml"),
        ]
    )

    assert status == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == [
        {"deduplication_key": "a", "functional_area": ["Planning"], "skills": []}
    ]


# --- salary priority: api (Phase 1) -> regex (Phase 2a) -> levels.fyi (Phase 2b) -> none ---

def _base_row(**overrides):
    row = {"deduplication_key": "a", "_classification": {"categories": ["Perception"], "skills": []}}
    row.update(overrides)
    return row


def test_salary_uses_phase1_api_field_when_present(tmp_path):
    path = tmp_path / "av_jobs.jsonl"
    _write_jsonl(
        path,
        [_base_row(salary_min=150000, salary_max=200000, salary_currency="USD", salary_period="yearly",
                   job_description="No numbers here that look like salary text.")],
    )

    record = _build([path])[0]

    assert record["salary_min"] == 150000
    assert record["salary_max"] == 200000
    assert record["salary_currency"] == "USD"
    assert record["salary_period"] == "yearly"
    assert record["salary_source"] == "api"


def test_salary_falls_through_to_regex_when_api_field_has_no_currency(tmp_path):
    # Regression test: a real Silver salary_min/salary_max with a null
    # salary_currency (e.g. the Greenhouse bronze model when the source
    # posting's pay_input_ranges entry has no currency_type) must not be
    # trusted as-is - salary_sync.sync_salary rejects a null currency, and
    # import_salary rolls back its *entire* batch on that one row's error.
    path = tmp_path / "av_jobs.jsonl"
    _write_jsonl(
        path,
        [_base_row(
            salary_min=150000, salary_max=200000, salary_currency=None, salary_period="yearly",
            job_description="The salary range for this position is $160,000 - $262,000 per year.",
        )],
    )

    record = _build([path])[0]

    assert record["salary_min"] == 160000.0
    assert record["salary_max"] == 262000.0
    assert record["salary_source"] == "regex"


def test_salary_falls_through_to_regex_when_api_field_has_no_period(tmp_path):
    path = tmp_path / "av_jobs.jsonl"
    _write_jsonl(
        path,
        [_base_row(
            salary_min=150000, salary_max=200000, salary_currency="USD", salary_period=None,
            job_description="The salary range for this position is $160,000 - $262,000 per year.",
        )],
    )

    record = _build([path])[0]

    assert record["salary_source"] == "regex"


def test_salary_falls_back_to_regex_when_no_api_field(tmp_path):
    path = tmp_path / "av_jobs.jsonl"
    _write_jsonl(
        path,
        [_base_row(job_description="The salary range for this position is $160,000 - $262,000 per year.")],
    )

    record = _build([path])[0]

    assert record["salary_min"] == 160000.0
    assert record["salary_max"] == 262000.0
    assert record["salary_currency"] == "USD"
    assert record["salary_period"] == "yearly"
    assert record["salary_source"] == "regex"


def test_salary_falls_back_to_levels_fyi_cache_when_no_api_or_regex_match(tmp_path):
    path = tmp_path / "av_jobs.jsonl"
    _write_jsonl(
        path,
        [_base_row(company_name="Waymo", job_description="No salary mentioned anywhere in this text.")],
    )
    cache_path = tmp_path / "company_salary.yaml"
    cache_path.write_text(yaml.safe_dump({
        "Waymo": {"avg_total_comp": 330413.0, "currency": "USD", "fetched_at": "2026-01-01T00:00:00+00:00"}
    }))

    record = _build([path], company_salary_cache_path=cache_path)[0]

    # A single company-wide median, not a real disclosed range for this
    # posting - goes to salary_average, not salary_min/salary_max (which
    # would otherwise look like a suspiciously exact min == max range).
    assert record["salary_average"] == 330413.0
    assert "salary_min" not in record
    assert "salary_max" not in record
    assert record["salary_currency"] == "USD"
    assert record["salary_period"] == "yearly"
    assert record["salary_source"] == "levels_fyi_average"


def test_salary_fields_absent_when_no_source_resolves(tmp_path):
    path = tmp_path / "av_jobs.jsonl"
    _write_jsonl(
        path,
        [_base_row(company_name="Unknown Co", job_description="Nothing salary-related here.")],
    )

    record = _build([path])[0]

    assert "salary_min" not in record
    assert "salary_source" not in record


def test_salary_source_counts_are_logged(tmp_path, caplog):
    path = tmp_path / "av_jobs.jsonl"
    _write_jsonl(
        path,
        [
            _base_row(deduplication_key="a", salary_min=1, salary_max=2, salary_currency="USD", salary_period="yearly"),
            {**_base_row(deduplication_key="b"), "deduplication_key": "b"},
        ],
    )

    with caplog.at_level("INFO"):
        _build([path])

    assert any("Salary resolved for 1/2" in message for message in caplog.messages)
