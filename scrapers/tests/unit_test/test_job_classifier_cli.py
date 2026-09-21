import json
from unittest.mock import patch

from scrapers.utils.job_classifier import (
    JobClassifierMain,
    _group_by_company_title,
    _job_key,
    _relevance_input,
)

ALIASES = {
    "company": ("company_name",),
    "title": ("job_name",),
    "description": ("job_description", "description"),
    "id": ("source_job_id", "deduplication_key", "id"),
}


def test_job_key_prefers_deduplication_key_over_the_audit_id_alias_chain():
    # source_job_id (a Greenhouse/SmartRecruiters numeric id or Workday
    # requisition number) is not unique across companies - deduplication_key
    # (the Silver MD5 natural-key hash) is the real identity.
    posting = {"source_job_id": "42", "deduplication_key": "abc123"}

    assert _job_key(posting, ALIASES) == "abc123"


def test_job_key_falls_back_to_audit_id_alias_chain_when_no_deduplication_key():
    posting = {"source_job_id": "42"}

    assert _job_key(posting, ALIASES) == "42"


def test_job_key_prevents_cross_company_source_job_id_collision():
    # Two unrelated jobs at different companies sharing a small numeric
    # source_job_id must not collide when used as a dict key.
    posting_a = {"source_job_id": "42", "deduplication_key": "dedupA", "company_name": "Company A"}
    posting_b = {"source_job_id": "42", "deduplication_key": "dedupB", "company_name": "Company B"}

    postings_by_id = {}
    for posting in (posting_a, posting_b):
        postings_by_id[_job_key(posting, ALIASES)] = posting

    assert len(postings_by_id) == 2
    assert postings_by_id["dedupA"]["company_name"] == "Company A"
    assert postings_by_id["dedupB"]["company_name"] == "Company B"


def test_relevance_input_combines_prefilter_keywords_and_short_excerpt():
    posting = {
        "job_description": "We build perception systems for self-driving cars using LiDAR and cameras.",
        "_prefilter": {"matched_keywords": ["autonomous", "lidar"]},
    }

    result = _relevance_input(posting, ALIASES, snippet_chars=30)

    assert "Keyword matches: autonomous, lidar" in result
    assert "Excerpt:" in result
    assert len(result) < len(posting["job_description"]) + 60


def test_relevance_input_falls_back_to_excerpt_only_when_no_keywords_matched():
    posting = {"job_description": "General office administration duties.", "_prefilter": {"matched_keywords": []}}

    result = _relevance_input(posting, ALIASES, snippet_chars=100)

    assert "Keyword matches" not in result
    assert "Excerpt: General office administration duties." in result


def test_relevance_input_handles_missing_prefilter_metadata():
    posting = {"job_description": "Some job text."}

    result = _relevance_input(posting, ALIASES, snippet_chars=50)

    assert "Excerpt: Some job text." in result


def test_group_by_company_title_collapses_exact_repeats_across_locations():
    postings = [
        ("id1", {"company_name": "GM", "job_name": "Senior Software Engineer", "job_description": "short"}),
        ("id2", {"company_name": "GM", "job_name": "Senior Software Engineer", "job_description": "much longer description"}),
        ("id3", {"company_name": "GM", "job_name": "Staff Software Engineer", "job_description": "different role"}),
    ]

    representatives, dedup_map = _group_by_company_title(postings, ALIASES)

    assert len(representatives) == 2
    rep_ids = {rep_id for rep_id, _ in representatives}
    assert rep_ids == {"id2", "id3"}
    assert sorted(dedup_map["id2"]) == ["id1", "id2"]
    assert dedup_map["id3"] == ["id3"]


def test_group_by_company_title_picks_longest_description_as_representative():
    postings = [
        ("short", {"company_name": "GM", "job_name": "Engineer", "job_description": "a"}),
        ("long", {"company_name": "GM", "job_name": "Engineer", "job_description": "a much longer description here"}),
    ]

    representatives, dedup_map = _group_by_company_title(postings, ALIASES)

    assert representatives[0][0] == "long"
    assert sorted(dedup_map["long"]) == ["long", "short"]


class _FakeClassifier:
    """Returns a prepared result per distinct request (keyed by the set of
    ids asked for, not call order, since retries iterate Python sets whose
    order isn't guaranteed) so the 3-tier retry (full batch -> group retry of
    the missing subset -> individual fallback) can be exercised
    deterministically regardless of set iteration order."""

    def __init__(self, responses_by_request):
        self.responses_by_request = {frozenset(k): v for k, v in responses_by_request.items()}
        self.calls: list[list[str]] = []

    def classify_batch(self, jobs):
        ids = [j["id"] for j in jobs]
        self.calls.append(ids)
        available = self.responses_by_request[frozenset(ids)]
        return {jid: available[jid] for jid in ids if jid in available}


def _jobs_by_id(*ids):
    return {jid: {"id": jid, "title": "x", "description": "y"} for jid in ids}


def test_retry_uses_one_group_call_not_individual_calls_when_group_retry_succeeds():
    from scrapers.service.llm import RelevanceDecision

    full = RelevanceDecision(True, "High", ())
    # First call (the full 3-job batch) only returns job "a"; "b" and "c" are
    # missing and should be retried together as ONE group call, not two
    # separate individual calls.
    classifier = _FakeClassifier(
        {
            ("a", "b", "c"): {"a": full},
            ("b", "c"): {"b": full, "c": full},
        }
    )

    results = JobClassifierMain._classify_with_retry(classifier, _jobs_by_id("a", "b", "c"), 1, 1)

    assert set(results) == {"a", "b", "c"}
    call_sets = [set(call) for call in classifier.calls]
    assert call_sets == [{"a", "b", "c"}, {"b", "c"}]


def test_retry_falls_back_to_individual_calls_only_for_still_missing_after_group_retry():
    from scrapers.service.llm import RelevanceDecision

    full = RelevanceDecision(True, "High", ())
    # Full batch returns only "a". Group retry of ["b", "c"] returns only "b".
    # Only "c" should need its own individual call after that.
    classifier = _FakeClassifier(
        {
            ("a", "b", "c"): {"a": full},
            ("b", "c"): {"b": full},
            ("c",): {"c": full},
        }
    )

    results = JobClassifierMain._classify_with_retry(classifier, _jobs_by_id("a", "b", "c"), 1, 1)

    assert set(results) == {"a", "b", "c"}
    call_sets = [set(call) for call in classifier.calls]
    assert call_sets[0] == {"a", "b", "c"}
    assert call_sets[1] == {"b", "c"}
    assert call_sets[2] == {"c"}


def test_retry_skips_group_retry_and_goes_straight_to_individual_on_total_failure():
    from scrapers.service.llm import RelevanceDecision

    full = RelevanceDecision(True, "High", ())
    # Full batch returns nothing at all (100% missing) - a same-size group
    # retry would just resend an identical request, so it should be skipped
    # entirely in favor of individual retries.
    classifier = _FakeClassifier(
        {
            ("a", "b"): {},
            ("a",): {"a": full},
            ("b",): {"b": full},
        }
    )

    results = JobClassifierMain._classify_with_retry(classifier, _jobs_by_id("a", "b"), 1, 1)

    assert set(results) == {"a", "b"}
    call_sets = [set(call) for call in classifier.calls]
    assert call_sets[0] == {"a", "b"}
    assert {frozenset(c) for c in call_sets[1:]} == {frozenset({"a"}), frozenset({"b"})}


class _RaisingThenWorkingClassifier:
    """Raises on the first call (simulating a 5xx / connection error /
    empty completion / truncated JSON the parser gave up on) and returns
    a real per-job result on every call after that."""

    def __init__(self):
        self.calls: list[list[str]] = []

    def classify_batch(self, jobs):
        from scrapers.service.llm import RelevanceDecision

        ids = [j["id"] for j in jobs]
        self.calls.append(ids)
        if len(self.calls) == 1:
            raise ConnectionError("simulated transient failure")
        return {jid: RelevanceDecision(True, "High", ()) for jid in ids}


def test_retry_falls_through_to_individual_calls_when_the_whole_batch_raises():
    # A batch-level exception must not mark every job in it permanently
    # failed after zero real per-job attempts - it should be treated like a
    # 100%-missing response and retried individually, same as a truncation.
    classifier = _RaisingThenWorkingClassifier()

    results = JobClassifierMain._classify_with_retry(classifier, _jobs_by_id("a", "b"), 1, 1)

    assert set(results) == {"a", "b"}
    # First call is the batch that raised; the rest are individual retries.
    assert classifier.calls[0] == ["a", "b"] or set(classifier.calls[0]) == {"a", "b"}
    assert {frozenset(c) for c in classifier.calls[1:]} == {frozenset({"a"}), frozenset({"b"})}


def test_group_by_company_title_no_duplicates_is_a_noop():
    postings = [
        ("id1", {"company_name": "GM", "job_name": "Engineer A", "job_description": "x"}),
        ("id2", {"company_name": "GM", "job_name": "Engineer B", "job_description": "y"}),
    ]

    representatives, dedup_map = _group_by_company_title(postings, ALIASES)

    assert len(representatives) == 2
    assert dedup_map == {"id1": ["id1"], "id2": ["id2"]}


class _GroupRetryRaisesClassifier:
    """First call (the full batch) leaves 2 of 3 jobs missing, which should
    trigger one smaller group retry - and that group retry call itself
    raises (a second 5xx/connection error), which must fall through to
    individual retries rather than propagating or giving up."""

    def __init__(self):
        self.calls: list[list[str]] = []

    def classify_batch(self, jobs):
        from scrapers.service.llm import RelevanceDecision

        ids = [j["id"] for j in jobs]
        self.calls.append(ids)
        if len(self.calls) == 1:
            return {"a": RelevanceDecision(True, "High", ())}
        if len(self.calls) == 2:
            raise ConnectionError("simulated group retry failure")
        return {jid: RelevanceDecision(True, "High", ()) for jid in ids}


def test_retry_falls_through_to_individual_calls_when_the_group_retry_itself_raises():
    classifier = _GroupRetryRaisesClassifier()

    results = JobClassifierMain._classify_with_retry(classifier, _jobs_by_id("a", "b", "c"), 1, 1)

    assert set(results) == {"a", "b", "c"}
    assert set(classifier.calls[0]) == {"a", "b", "c"}
    assert set(classifier.calls[1]) == {"b", "c"}
    assert {frozenset(c) for c in classifier.calls[2:]} == {frozenset({"b"}), frozenset({"c"})}


def _fake_relevance_complete(_prompt: str) -> str:
    """Always offers a result for both ids this file's tests use, regardless
    of which one the prompt actually asked about - JobClassifier.parse_response
    already filters a batch response down to only the requested ids, so
    returning extras is harmless. This avoids re-parsing the prompt text: its
    own instructional prose contains the literal string "<jobs_json>" (as an
    example placeholder name) without a matching closing tag, which made an
    earlier, prompt-parsing version of this helper fragile."""
    results = [
        {"id": job_id, "is_av_relevant": True, "confidence": "High", "matched_keywords": []}
        for job_id in ("existing-1", "new-2")
    ]
    return json.dumps({"results": results})


@patch("scrapers.utils.job_classifier.GroqCompletion")
def test_main_resumes_and_skips_already_processed_job_ids(mock_groq_completion, tmp_path):
    mock_groq_completion.return_value.side_effect = _fake_relevance_complete

    input_path = tmp_path / "llm_candidates.jsonl"
    with input_path.open("w", encoding="utf-8") as stream:
        stream.write(json.dumps({"deduplication_key": "existing-1", "job_name": "Old Role"}) + "\n")
        stream.write(json.dumps({"deduplication_key": "new-2", "job_name": "New Role"}) + "\n")

    output_dir = tmp_path / "job_classification"
    output_dir.mkdir()
    (output_dir / "av_candidates.jsonl").write_text(
        json.dumps({"deduplication_key": "existing-1", "_job_id": "existing-1"}) + "\n", encoding="utf-8"
    )

    status = JobClassifierMain.main(["--input", str(input_path), "--output-dir", str(output_dir)])

    assert status == 0
    av_lines = (output_dir / "av_candidates.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(av_lines) == 2
    job_ids = {json.loads(line)["_job_id"] for line in av_lines}
    assert job_ids == {"existing-1", "new-2"}

    metrics = json.loads((output_dir / "relevance_metrics.json").read_text(encoding="utf-8"))
    assert metrics["skipped_already_processed"] == 1
    # av_candidates counts the whole file (pre-existing line included), not
    # just this run's own additions.
    assert metrics["av_candidates"] == 2
