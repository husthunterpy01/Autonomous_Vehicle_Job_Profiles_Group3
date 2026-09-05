import json

from scrapers.service.job_prefilter import (
    AuditCategoryRule,
    JobFilterConfig,
    JobPrefilter,
)


def make_filter() -> JobPrefilter:
    return JobPrefilter(
        JobFilterConfig(
            minimum_score=3,
            exclude_below_threshold=False,
            field_weights={"title": 3, "department": 2, "description": 1},
            positive_keywords=("autonomous", "perception", "software"),
            excluded_title_keywords=("accountant", "marketing"),
            excluded_category_rules=(
                AuditCategoryRule(
                    name="Finance / Accounting",
                    keywords=("accountant", "financial statements"),
                ),
                AuditCategoryRule(
                    name="Communications / Marketing",
                    keywords=("marketing", "media relations"),
                ),
            ),
            default_excluded_category="Corporate / Support",
            field_aliases={
                "id": ("id",),
                "company": ("company_name",),
                "title": ("job_name",),
                "description": ("job_description",),
                "department": ("department",),
            },
        )
    )


def test_filter_excludes_non_av_title_despite_company_boilerplate():
    posting = {
        "id": 1,
        "company_name": "Example AV",
        "job_name": "Senior Accountant",
        "job_description": "We build autonomous perception software.",
    }

    decision = make_filter().evaluate(posting)

    assert decision.included is False
    assert decision.reason == "excluded_title_keyword"
    assert decision.excluded_title_keywords == ("accountant",)
    assert decision.audit_category == "Finance / Accounting"
    assert decision.category_evidence == ("accountant",)


def test_filter_includes_relevant_job_from_title_score():
    posting = {
        "id": "av-2",
        "company_name": "Example AV",
        "job_name": "Perception Engineer",
        "job_description": "Build production systems.",
    }

    decision = make_filter().evaluate(posting)

    assert decision.included is True
    assert decision.score == 3
    assert decision.reason == "score_at_or_above_threshold"


def test_filter_retains_excluded_rows_and_reports_company_reduction():
    postings = [
        {
            "id": "1",
            "company_name": "A",
            "job_name": "Software Engineer",
            "job_description": "Build systems.",
        },
        {
            "id": "2",
            "company_name": "A",
            "job_name": "Marketing Manager",
            "job_description": "Promote autonomous software.",
        },
        {
            "id": "3",
            "company_name": "B",
            "job_name": "Accountant",
            "job_description": "Coordinate calendars.",
        },
    ]

    result = make_filter().filter(postings)

    assert result.before_count == 3
    assert result.after_count == 1
    assert len(result.excluded) == 2
    assert result.excluded[0]["_prefilter"]["reason"] == "excluded_title_keyword"
    assert result.company_metrics == (
        {
            "company": "A",
            "before_count": 2,
            "after_count": 1,
            "excluded_count": 1,
            "reduction_percent": 50.0,
        },
        {
            "company": "B",
            "before_count": 1,
            "after_count": 0,
            "excluded_count": 1,
            "reduction_percent": 100.0,
        },
    )


def test_write_outputs_creates_llm_audit_and_metrics_files(tmp_path):
    result = make_filter().filter(
        [
            {
                "id": "1",
                "company_name": "A",
                "job_name": "Software Engineer",
                "job_description": "Build systems.",
            },
            {
                "id": "2",
                "company_name": "A",
                "job_name": "Accountant",
                "job_description": "Support autonomous software teams.",
            },
        ]
    )

    paths = result.write_outputs(tmp_path)

    candidates = paths["llm_candidates"].read_text(encoding="utf-8").splitlines()
    excluded = paths["excluded_audit"].read_text(encoding="utf-8").splitlines()
    metrics = json.loads(paths["metrics"].read_text(encoding="utf-8"))
    assert len(candidates) == 1
    assert len(excluded) == 1
    assert json.loads(excluded[0])["id"] == "2"
    assert metrics[0]["reduction_percent"] == 50.0


def test_external_yaml_changes_threshold_without_code_change(tmp_path):
    config_path = tmp_path / "filter.yaml"
    config_path.write_text(
        """
minimum_score: 2
exclude_below_threshold: true
field_weights:
  title: 1
  description: 1
field_aliases:
  id: [id]
  company: [company]
  title: [title]
  description: [description]
positive_keywords: [autonomous, robotics]
excluded_title_keywords: [accountant]
excluded_category_rules:
  - name: Finance / Accounting
    keywords: [accountant]
default_excluded_category: Corporate / Support
""".strip(),
        encoding="utf-8",
    )
    posting = {
        "id": "1",
        "company": "A",
        "title": "Robotics role",
        "description": "Autonomous systems",
    }

    decision = JobPrefilter.from_config(config_path).evaluate(posting)

    assert decision.included is True
    assert decision.score == 2


def test_safe_mode_keeps_unknown_roles_for_llm_review():
    posting = {
        "id": "unknown-1",
        "company_name": "A",
        "job_name": "Electrical Engineer, Compute",
        "job_description": "Design production systems.",
    }

    decision = make_filter().evaluate(posting)

    assert decision.included is True
    assert decision.score == 0
    assert decision.reason == "included_for_llm_review"


def test_audit_output_converts_nan_to_json_null(tmp_path):
    result = make_filter().filter(
        [
            {
                "id": "nan-1",
                "company_name": "A",
                "job_name": "Accountant",
                "job_description": float("nan"),
            }
        ]
    )

    path = result.write_outputs(tmp_path)["excluded_audit"]
    audit_row = json.loads(path.read_text(encoding="utf-8"))

    assert audit_row["job_description"] is None


def test_excluded_category_can_use_description_when_title_is_generic():
    description_filter = JobPrefilter(
        JobFilterConfig(
            minimum_score=3,
            exclude_below_threshold=False,
            field_weights={"title": 3, "description": 1},
            positive_keywords=("autonomous",),
            excluded_title_keywords=("office manager",),
            excluded_category_rules=(
                AuditCategoryRule(
                    name="Communications / Public Relations",
                    keywords=("media relations",),
                ),
            ),
            default_excluded_category="Corporate / Support",
            field_aliases={
                "id": ("id",),
                "company": ("company_name",),
                "title": ("job_name",),
                "description": ("job_description",),
            },
        )
    )
    posting = {
        "id": "description-1",
        "company_name": "A",
        "job_name": "Office Manager",
        "job_description": "Own executive media relations and press strategy.",
    }

    decision = description_filter.evaluate(posting)

    assert decision.included is False
    assert decision.audit_category == "Communications / Public Relations"
    assert decision.category_evidence == ("media relations",)
