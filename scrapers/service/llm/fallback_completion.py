from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import replace

from scrapers.config.groq import GroqConfig
from scrapers.service.llm.groq_client import GroqCompletion
from scrapers.service.llm.provider_errors import ProviderRateLimitExhausted

logger = logging.getLogger(__name__)


class FallbackCompletion:
    """Use a primary complete(prompt) until its quota is spent, then stick with fallback.

    Groq free-tier TPM/RPM are per model id, so gpt-oss-20b can 429 while
    gpt-oss-120b on the same key pool still has headroom.
    """

    def __init__(
        self,
        primary: Callable[[str], str],
        fallback: Callable[[str], str],
        fallback_label: str = "fallback",
    ) -> None:
        self.primary = primary
        self.fallback = fallback
        self.fallback_label = fallback_label
        self._using_fallback = False

    def __call__(self, prompt: str) -> str:
        if self._using_fallback:
            return self.fallback(prompt)
        try:
            return self.primary(prompt)
        except ProviderRateLimitExhausted:
            logger.warning(
                "Primary Groq model is rate-limited; switching to %s for the rest of this run.",
                self.fallback_label,
            )
            self._using_fallback = True
            return self.fallback(prompt)


def build_groq_completion(config: GroqConfig | None = None) -> Callable[[str], str]:
    """gpt-oss-20b first, then gpt-oss-120b on the same Groq key pool after 429s."""
    config = config or GroqConfig()
    fallback_model = config.fallback_model
    if not fallback_model or fallback_model == config.model:
        return GroqCompletion(config)
    logger.info(
        "Groq completion: primary=%s, fallback=%s after 3 consecutive 429s.",
        config.model,
        fallback_model,
    )
    primary = GroqCompletion(replace(config, fail_after_key_pool_exhausted=True))
    fallback = GroqCompletion(
        replace(config, model=fallback_model, fail_after_key_pool_exhausted=False)
    )
    return FallbackCompletion(primary, fallback, fallback_label=fallback_model)
