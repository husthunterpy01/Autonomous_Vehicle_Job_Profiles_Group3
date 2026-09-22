from scrapers.config.groq import GroqConfig
from scrapers.service.llm.fallback_completion import (
    FallbackCompletion,
    build_groq_completion,
)
from scrapers.service.llm.provider_errors import ProviderRateLimitExhausted


def test_fallback_switches_to_120b_after_20b_pool_exhaustion():
    calls = []

    def primary(_prompt):
        calls.append("20b")
        raise ProviderRateLimitExhausted("20b spent")

    def fallback(_prompt):
        calls.append("120b")
        return '{"ok": true}'

    complete = FallbackCompletion(primary, fallback, fallback_label="openai/gpt-oss-120b")
    assert complete("first") == '{"ok": true}'
    assert complete("second") == '{"ok": true}'
    assert calls == ["20b", "120b", "120b"]


def test_build_groq_completion_wraps_20b_then_120b(monkeypatch):
    captured = []

    class FakeCompletion:
        def __init__(self, config):
            captured.append(config.model)
            self.config = config

        def __call__(self, prompt):
            return prompt

    monkeypatch.setattr("scrapers.service.llm.fallback_completion.GroqCompletion", FakeCompletion)
    complete = build_groq_completion(GroqConfig(api_key="test-key"))
    assert isinstance(complete, FallbackCompletion)
    assert captured == ["openai/gpt-oss-20b", "openai/gpt-oss-120b"]
    assert complete.primary.config.fail_after_key_pool_exhausted is True
    assert complete.fallback.config.model == "openai/gpt-oss-120b"


def test_build_groq_completion_skips_wrapper_when_fallback_disabled():
    from scrapers.service.llm.groq_client import GroqCompletion

    config = GroqConfig(api_key="test-key", fallback_model="")
    complete = build_groq_completion(config)
    assert isinstance(complete, GroqCompletion)
    assert complete.config.model == "openai/gpt-oss-20b"


def test_build_groq_completion_skips_wrapper_when_models_match(monkeypatch):
    captured = []

    class FakeCompletion:
        def __init__(self, config):
            captured.append((config.model, config.fail_after_key_pool_exhausted))

    monkeypatch.setattr("scrapers.service.llm.fallback_completion.GroqCompletion", FakeCompletion)
    config = GroqConfig(
        api_key="test-key",
        model="openai/gpt-oss-120b",
        fallback_model="openai/gpt-oss-120b",
    )
    complete = build_groq_completion(config)
    assert not isinstance(complete, FallbackCompletion)
    assert captured == [("openai/gpt-oss-120b", False)]
