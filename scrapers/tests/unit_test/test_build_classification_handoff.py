import json
import logging

import pytest
import yaml
from scrapers.utils.build_classification_handoff import DEFAULT_MAIN_TYPES_PATH, _load_main_types, build_handoff_records, main


def _write_jsonl(path, rows):
    with path.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row) + "\n")


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

    records = build_handoff_records([path], main_types_path=None)

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

    records = build_handoff_records([path], main_types_path=main_types_path)

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
        records = build_handoff_records([path], main_types_path=main_types_path)

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
    assert mapping.get("Perception") == "Perception"


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

    assert build_handoff_records([path], main_types_path=None) == []


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

    records = build_handoff_records([keyword_path, llm_path], main_types_path=None)

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
        ]
    )

    assert status == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == [
        {"deduplication_key": "a", "functional_area": ["Planning"], "skills": []}
    ]
