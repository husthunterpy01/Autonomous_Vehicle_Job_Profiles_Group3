import json
from decimal import Decimal

from scrapers.service.llm.io import JobPostingIO


def test_json_safe_coerces_decimal_to_float():
    assert JobPostingIO.json_safe(Decimal("135000.00")) == 135000.0
    assert isinstance(JobPostingIO.json_safe(Decimal("135000.00")), float)


def test_json_safe_coerces_decimal_inside_nested_structures():
    value = {"salary_min": Decimal("135000.00"), "items": [Decimal(1), {"nested": Decimal("2.5")}]}
    safe = JobPostingIO.json_safe(value)
    assert safe == {"salary_min": 135000.0, "items": [1.0, {"nested": 2.5}]}


def test_write_json_lines_writes_decimal_as_a_real_json_number_not_a_string(tmp_path):
    # Regression test: Postgres NUMERIC columns (e.g. Silver's salary_min/
    # salary_max) come back from psycopg2 as Decimal. Without coercion,
    # json.dumps's default=str stringifies it ("135000.00") instead of
    # writing a real JSON number - a silent type change that only breaks
    # downstream when something asserts isinstance(value, (int, float)),
    # like salary_sync.sync_salary.
    path = tmp_path / "out.jsonl"
    JobPostingIO.write_json_lines(path, [{"salary_min": Decimal("135000.00")}])

    reparsed = json.loads(path.read_text().splitlines()[0])
    assert reparsed["salary_min"] == 135000.0
    assert isinstance(reparsed["salary_min"], float)
