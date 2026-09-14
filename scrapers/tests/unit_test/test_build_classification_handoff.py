import json

import yaml

from scrapers.utils.build_classification_handoff import build_handoff_records, main


def _write_jsonl(path, rows):
    with path.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row) + "\n")


def _build(paths, **kwargs):
    kwargs.setdefault("main_types_path", None)
    kwargs.setdefault("company_salary_cache_path", None)
    return build_handoff_records(paths, **kwargs)


def test_reshapes_categories_into_functional_area_objects(tmp_path):
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
            "functional_area": [{"sub_type": "Perception", "main_type": None}],
            "skills": [{"name": "ROS 2", "skill_type": "framework"}],
        }
    ]


def test_attaches_main_type_from_mapping_file(tmp_path):
    path = tmp_path / "av_jobs.jsonl"
    _write_jsonl(
        path,
        [{"deduplication_key": "a", "_classification": {"categories": ["Perception", "Sensing"], "skills": []}}],
    )
    main_types_path = tmp_path / "category_main_types.yaml"
    main_types_path.write_text(yaml.safe_dump({"Perception": "Perception & Sensing", "Sensing": "Perception & Sensing"}))

    records = _build([path], main_types_path=main_types_path)

    assert records[0]["functional_area"] == [
        {"sub_type": "Perception", "main_type": "Perception & Sensing"},
        {"sub_type": "Sensing", "main_type": "Perception & Sensing"},
    ]


def test_unmapped_category_gets_null_main_type(tmp_path):
    path = tmp_path / "av_jobs.jsonl"
    _write_jsonl(
        path,
        [{"deduplication_key": "a", "_classification": {"categories": ["Perception"], "skills": []}}],
    )
    main_types_path = tmp_path / "category_main_types.yaml"
    main_types_path.write_text(yaml.safe_dump({"Sensing": "Perception & Sensing"}))

    records = _build([path], main_types_path=main_types_path)

    assert records[0]["functional_area"] == [{"sub_type": "Perception", "main_type": None}]


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
    assert records[0]["functional_area"] == [{"sub_type": "Perception", "main_type": None}]


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
        {"deduplication_key": "a", "functional_area": [{"sub_type": "Planning", "main_type": None}], "skills": []}
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

    assert record["salary_min"] == 330413.0
    assert record["salary_max"] == 330413.0
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
