from types import SimpleNamespace

import pytest
from scrapers.config.groq import GroqConfig
from scrapers.service.llm.groq_client import GroqCompletion, _FixedWindowRateLimiter


def test_raises_without_api_key():
    with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
        GroqCompletion(GroqConfig(api_key=""))


def test_builds_client_when_api_key_present():
    completion = GroqCompletion(GroqConfig(api_key="test-key"))
    assert completion.config.api_key == "test-key"


def test_limiter_does_not_wait_when_budget_is_untouched():
    limiter = _FixedWindowRateLimiter(tokens_per_minute=8000)
    limiter.wait_for_capacity()  # should return immediately, no sleep


def test_limiter_paces_off_actual_recorded_usage_not_a_fixed_estimate(monkeypatch):
    """A call whose real usage is small should not exhaust the budget just
    because a caller's worst-case estimate would have - this is the bug that
    made every call sleep out a full window regardless of actual cost."""
    limiter = _FixedWindowRateLimiter(tokens_per_minute=8000)
    limiter.reconcile(0, 500)  # a small completion actually cost 500 tokens

    slept = []
    monkeypatch.setattr("scrapers.service.llm.groq_client.time.sleep", slept.append)
    limiter.wait_for_capacity()
    assert slept == []  # far under budget, so no pacing sleep


def test_limiter_waits_once_recorded_usage_reaches_budget(monkeypatch):
    limiter = _FixedWindowRateLimiter(tokens_per_minute=8000, safety_ratio=0.85)
    limiter.reconcile(0, 6800)  # exactly the budget

    slept = []
    monkeypatch.setattr("scrapers.service.llm.groq_client.time.sleep", slept.append)
    limiter.wait_for_capacity()
    assert len(slept) == 1
    assert slept[0] > 0


def test_limiter_resets_after_a_window_elapses(monkeypatch):
    limiter = _FixedWindowRateLimiter(tokens_per_minute=8000)
    limiter.reconcile(0, 6800)

    clock = {"now": limiter._window_start + 61}
    monkeypatch.setattr("scrapers.service.llm.groq_client.time.monotonic", lambda: clock["now"])
    slept = []
    monkeypatch.setattr("scrapers.service.llm.groq_client.time.sleep", slept.append)

    limiter.wait_for_capacity()
    assert slept == []  # window already elapsed, no need to sleep
    assert limiter._used == 0.0


def test_reservation_gates_admission_when_estimate_exceeds_headroom(monkeypatch):
    """Regression test for the tail-of-window overshoot: previously nothing
    was reserved before a call, so a request whose real cost would blow
    through the remaining budget was admitted anyway, and a 429 from that
    overshoot wasn't charged against the window either. Reserving a cheap
    pre-call estimate must gate admission on it instead."""
    limiter = _FixedWindowRateLimiter(tokens_per_minute=10000)  # budget = 8500
    limiter.reconcile(0, 7300)  # used=7300 -> only 1200 headroom left

    slept = []
    monkeypatch.setattr("scrapers.service.llm.groq_client.time.sleep", slept.append)
    limiter.wait_for_capacity(reserved_tokens=2500)  # this call is estimated at 2500 tokens

    assert len(slept) == 1  # must wait out the window instead of overshooting it
    assert limiter._used == 2500  # window reset, then this call's reservation committed


def _fake_response(content: str, total_tokens: int | None, completion_tokens: int | None = None):
    usage = (
        SimpleNamespace(total_tokens=total_tokens, completion_tokens=completion_tokens)
        if total_tokens is not None
        else None
    )
    message = SimpleNamespace(content=content)
    choice = SimpleNamespace(message=message, finish_reason="stop")
    return SimpleNamespace(choices=[choice], usage=usage)


class _FakeRawResponse:
    def __init__(self, response):
        self._response = response

    def parse(self):
        return self._response


def test_call_paces_using_real_usage_from_the_response(monkeypatch):
    """Regression test: the limiter must be paced from the server-reported
    usage, not from len(prompt)//4 + max_completion_tokens - previously that
    pessimistic estimate alone was often close to the whole per-minute
    budget, so the limiter slept before nearly every call."""
    completion = GroqCompletion(GroqConfig(api_key="test-key", max_completion_tokens=4096))

    def fake_create(**kwargs):
        return _FakeRawResponse(_fake_response('{"ok": true}', total_tokens=42, completion_tokens=30))

    completion._hub._clients[0] = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(with_raw_response=SimpleNamespace(create=fake_create)))
    )

    result = completion("short prompt")
    assert result == '{"ok": true}'
    # Reconciled to the real usage regardless of what was reserved pre-call.
    assert completion._hub.limiter._used == 42


def test_config_builds_single_key_pool_from_explicit_api_key():
    config = GroqConfig(api_key="test-key")
    assert config.api_keys == ("test-key",)


def test_config_splits_comma_separated_keys_from_one_variable():
    config = GroqConfig(api_key="key-one, key-two ,key-one")
    assert config.api_keys == ("key-one", "key-two")


def test_rotates_to_next_key_after_more_than_three_consecutive_rate_limits(monkeypatch):
    """Regression test for the key-hub: a key stuck on repeated 429s should
    be abandoned in favor of the next one in the pool rather than retried
    forever, and the call should still succeed once the new key works."""
    import groq
    import httpx

    config = GroqConfig(api_key="key-one", api_keys=("key-one", "key-two"))
    completion = GroqCompletion(config)

    monkeypatch.setattr("scrapers.service.llm.groq_client.time.sleep", lambda _seconds: None)

    def make_rate_limit_error():
        request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
        response = httpx.Response(status_code=429, request=request)
        return groq.RateLimitError("rate limited", response=response, body=None)

    calls = []

    def failing_create(**kwargs):
        calls.append("key-one")
        raise make_rate_limit_error()

    def succeeding_create(**kwargs):
        calls.append("key-two")
        return _FakeRawResponse(_fake_response('{"ok": true}', total_tokens=10, completion_tokens=5))

    completion._hub._clients[0] = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(with_raw_response=SimpleNamespace(create=failing_create)))
    )
    completion._hub._clients[1] = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(with_raw_response=SimpleNamespace(create=succeeding_create)))
    )

    result = completion("short prompt")

    assert result == '{"ok": true}'
    assert calls == ["key-one", "key-one", "key-one", "key-one", "key-two"]
    assert completion._hub._index == 1


def test_raises_after_max_total_wait_instead_of_retrying_forever(monkeypatch):
    """Regression test: with a single key, rotate() can never help, so a
    persistent (e.g. daily-quota) 429 must not retry forever - it should
    raise once the cumulative backoff exceeds the cap instead of hanging the
    calling pipeline stage indefinitely."""
    import groq
    import httpx

    config = GroqConfig(api_key="only-key")
    completion = GroqCompletion(config)

    monkeypatch.setattr("scrapers.service.llm.groq_client.time.sleep", lambda _seconds: None)

    def make_rate_limit_error():
        request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
        response = httpx.Response(status_code=429, request=request)
        return groq.RateLimitError("rate limited", response=response, body=None)

    calls = []

    def always_failing_create(**kwargs):
        calls.append(1)
        raise make_rate_limit_error()

    completion._hub._clients[0] = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(with_raw_response=SimpleNamespace(create=always_failing_create)))
    )

    with pytest.raises(RuntimeError, match="quota exhaustion"):
        completion("short prompt")

    # It must have actually given up rather than looping forever.
    assert 0 < len(calls) < 1000


def test_reservation_committed_once_not_per_retry_attempt(monkeypatch):
    """A flaky sequence of 429s on the same key must reserve this call's
    estimate once, not once per retry - otherwise the reservation would be
    double- (or triple-) counted against the window for one logical call."""
    import groq
    import httpx

    config = GroqConfig(api_key="only-key")
    completion = GroqCompletion(config)
    monkeypatch.setattr("scrapers.service.llm.groq_client.time.sleep", lambda _seconds: None)

    def make_rate_limit_error():
        request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
        response = httpx.Response(status_code=429, request=request)
        return groq.RateLimitError("rate limited", response=response, body=None)

    attempts = {"count": 0}

    def flaky_create(**kwargs):
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise make_rate_limit_error()
        return _FakeRawResponse(_fake_response('{"ok": true}', total_tokens=10, completion_tokens=5))

    completion._hub._clients[0] = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(with_raw_response=SimpleNamespace(create=flaky_create)))
    )

    reservations = []
    limiter = completion._hub.limiter
    original_wait_for_capacity = limiter.wait_for_capacity

    def spy(reserved_tokens=0.0):
        reservations.append(reserved_tokens)
        return original_wait_for_capacity(reserved_tokens)

    monkeypatch.setattr(limiter, "wait_for_capacity", spy)

    result = completion("short prompt")

    assert result == '{"ok": true}'
    assert attempts["count"] == 3
    assert len(reservations) == 1  # reserved once for the whole retry sequence
    assert limiter._used == 10  # reconciled to the eventual real usage


def test_reservation_uses_running_average_completion_tokens(monkeypatch):
    """The pre-call estimate should tighten as real completion sizes come
    in, instead of staying at the pessimistic max_completion_tokens ceiling
    or at a naive zero forever."""
    completion = GroqCompletion(GroqConfig(api_key="test-key"))
    monkeypatch.setattr("scrapers.service.llm.groq_client.time.sleep", lambda _seconds: None)

    def fake_create(**kwargs):
        return _FakeRawResponse(_fake_response('{"ok": true}', total_tokens=1000, completion_tokens=800))

    completion._hub._clients[0] = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(with_raw_response=SimpleNamespace(create=fake_create)))
    )

    completion("prompt one")
    assert completion._avg_completion_tokens == 800

    reservations = []
    limiter = completion._hub.limiter
    original_wait_for_capacity = limiter.wait_for_capacity

    def spy(reserved_tokens=0.0):
        reservations.append(reserved_tokens)
        return original_wait_for_capacity(reserved_tokens)

    monkeypatch.setattr(limiter, "wait_for_capacity", spy)

    completion("prompt two")
    assert reservations[0] == pytest.approx(len("prompt two") / 4 + 800)
