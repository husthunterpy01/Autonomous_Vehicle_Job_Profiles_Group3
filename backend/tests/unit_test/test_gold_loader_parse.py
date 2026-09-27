"""DOC-13: parsing a run's av_jobs.jsonl for the gold loader (no database)."""
import json
from datetime import timedelta

import pytest

from app.services.gold_loader import GoldLoader, parse_run, parse_scraped_at, read_jsonl

KEY_A = "a" * 32
KEY_B = "b" * 32


def job(key=KEY_A, title="Perception Engineer", skills=None, categories=None, relevant="True"):
    return {
        "deduplication_key": key,
        "job_name": title,
        "_classification": {
            "is_av_relevant": relevant,
            "categories": categories or [],
            "skills": skills if skills is not None else [{"name": "LiDAR", "skill_type": "domain_concept"}],
        },
    }


def test_parses_title_skills_and_main_type():
    jobs, skipped = parse_run([job(title="  Perception   Engineer ", categories=["Perception", "Sensing"])])
    assert skipped == 0
    assert jobs[0].title == "Perception Engineer"
    assert jobs[0].main_type == "Perception & Sensing"
    assert jobs[0].skills == (("lidar", "domain_concept", "LiDAR"),)


def test_main_type_takes_the_largest_group_then_the_first_listed():
    jobs, _ = parse_run([
        job(KEY_A, categories=["Planning", "Control", "System and Safety"]),
        job(KEY_B, categories=["Planning", "Control"]),
    ])
    assert jobs[0].main_type == "System"
    assert jobs[1].main_type == "Decision"


def test_no_or_unknown_categories_give_no_main_type():
    jobs, _ = parse_run([job(KEY_A, categories=[]), job(KEY_B, categories=["Not A Category"])])
    assert [j.main_type for j in jobs] == [None, None]


def test_skills_are_normalized_like_the_backend_and_deduplicated():
    jobs, _ = parse_run([job(skills=[
        {"name": "Machine  Learning", "skill_type": "domain_concept"},
        {"name": "machine learning", "skill_type": "domain_concept"},
        {"name": "PyTorch", "skill_type": "framework"},
    ])])
    assert jobs[0].skills == (
        ("machine learning", "domain_concept", "Machine  Learning"),
        ("pytorch", "framework", "PyTorch"),
    )


def test_a_job_without_skills_is_kept():
    jobs, _ = parse_run([job(skills=[])])
    assert jobs[0].skills == ()


@pytest.mark.parametrize("relevant", ["False", "false", False])
def test_rows_marked_not_av_are_skipped(relevant):
    jobs, skipped = parse_run([job(relevant=relevant)])
    assert (jobs, skipped) == ([], 1)


@pytest.mark.parametrize(
    ("row", "message"),
    [
        ({**job(), "deduplication_key": "not-md5"}, "deduplication_key"),
        ({**job(), "job_name": " "}, "job_name"),
        ({"deduplication_key": KEY_A, "job_name": "x"}, "_classification"),
        (job(skills=[{"name": "LiDAR", "skill_type": "hardware"}]), "Invalid extracted skill"),
    ],
)
def test_malformed_rows_reject_the_run(row, message):
    with pytest.raises(ValueError, match=message):
        parse_run([row])


def test_duplicate_jobs_in_a_run_are_rejected():
    with pytest.raises(ValueError, match="Row 2: Duplicate deduplication_key"):
        parse_run([job(), job()])


def test_scraped_at_needs_a_timezone():
    assert parse_scraped_at("2026-08-31T12:00:00Z").utcoffset() == timedelta(0)
    assert parse_scraped_at("2026-09-01T02:00:00+08:00").utcoffset() == timedelta(hours=8)
    with pytest.raises(ValueError, match="timezone"):
        parse_scraped_at("2026-08-31T12:00:00")
    with pytest.raises(ValueError, match="ISO 8601"):
        parse_scraped_at("31/08/2026")


def test_read_jsonl_skips_blank_lines_and_reports_bad_ones(tmp_path):
    path = tmp_path / "av_jobs.jsonl"
    path.write_text(json.dumps(job()) + "\n\n" + json.dumps(job(KEY_B)) + "\n", encoding="utf-8")
    assert len(read_jsonl(path)) == 2
    path.write_text(json.dumps(job()) + "\n{broken\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Line 2"):
        read_jsonl(path)


def test_loader_rejects_unsafe_schema_names():
    with pytest.raises(ValueError, match="schema"):
        GoldLoader(engine=None, schema='gold"; DROP TABLE x; --')
