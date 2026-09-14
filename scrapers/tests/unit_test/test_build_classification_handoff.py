import json

import yaml
from scrapers.utils.build_classification_handoff import build_handoff_records, main


def _write_jsonl(path, rows):
    with path.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row) + "\n")


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

    records = build_handoff_records([path], main_types_path=None)

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

    records = build_handoff_records([path], main_types_path=main_types_path)

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

    records = build_handoff_records([path], main_types_path=main_types_path)

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
        ]
    )

    assert status == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == [
        {"deduplication_key": "a", "functional_area": [{"sub_type": "Planning", "main_type": None}], "skills": []}
    ]
