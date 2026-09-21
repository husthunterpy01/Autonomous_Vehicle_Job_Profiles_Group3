import json
from unittest.mock import patch

import yaml
from scrapers.service.llm.job_enricher import ALLOWED_CATEGORIES
from scrapers.utils.extract_category_taxonomy import main


def _fake_taxonomy_response() -> str:
    return json.dumps(
        {
            "categories": [
                {"sub_type": sub_type, "main_type": "Software"} for sub_type in sorted(ALLOWED_CATEGORIES)
            ]
        }
    )


@patch("scrapers.utils.extract_category_taxonomy.GroqCompletion")
def test_main_writes_taxonomy_mapping_to_the_requested_output(mock_groq_completion, tmp_path):
    mock_groq_completion.return_value.side_effect = lambda _prompt: _fake_taxonomy_response()
    output_path = tmp_path / "category_main_types.yaml"

    status = main(["--output", str(output_path)])

    assert status == 0
    assert output_path.is_file()
    mapping = yaml.safe_load(output_path.read_text(encoding="utf-8"))
    assert set(mapping) == ALLOWED_CATEGORIES
    assert all(main_type == "Software" for main_type in mapping.values())


@patch("scrapers.utils.extract_category_taxonomy.GroqCompletion")
def test_main_creates_parent_directory(mock_groq_completion, tmp_path):
    mock_groq_completion.return_value.side_effect = lambda _prompt: _fake_taxonomy_response()
    output_path = tmp_path / "nested" / "category_main_types.yaml"

    status = main(["--output", str(output_path)])

    assert status == 0
    assert output_path.is_file()
