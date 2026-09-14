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
    limiter.record(500)  # a small completion actually cost 500 tokens

    slept = []
    monkeypatch.setattr("scrapers.service.llm.groq_client.time.sleep", slept.append)
    limiter.wait_for_capacity()
    assert slept == []  # far under budget, so no pacing sleep


def test_limiter_waits_once_recorded_usage_reaches_budget(monkeypatch):
    limiter = _FixedWindowRateLimiter(tokens_per_minute=8000, safety_ratio=0.85)
    limiter.record(6800)  # exactly the budget

    slept = []
    monkeypatch.setattr("scrapers.service.llm.groq_client.time.sleep", slept.append)
    limiter.wait_for_capacity()
    assert len(slept) == 1
    assert slept[0] > 0


def test_limiter_resets_after_a_window_elapses(monkeypatch):
    limiter = _FixedWindowRateLimiter(tokens_per_minute=8000)
    limiter.record(6800)

    clock = {"now": limiter._window_start + 61}
    monkeypatch.setattr("scrapers.service.llm.groq_client.time.monotonic", lambda: clock["now"])
    slept = []
    monkeypatch.setattr("scrapers.service.llm.groq_client.time.sleep", slept.append)

    limiter.wait_for_capacity()
    assert slept == []  # window already elapsed, no need to sleep
    assert limiter._used == 0.0


def _fake_response(content: str, total_tokens: int | None):
    usage = SimpleNamespace(total_tokens=total_tokens) if total_tokens is not None else None
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
        return _FakeRawResponse(_fake_response('{"ok": true}', total_tokens=42))

    completion._hub._clients[0] = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(with_raw_response=SimpleNamespace(create=fake_create)))
    )

    result = completion("short prompt")
    assert result == '{"ok": true}'
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
        return _FakeRawResponse(_fake_response('{"ok": true}', total_tokens=10))

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
