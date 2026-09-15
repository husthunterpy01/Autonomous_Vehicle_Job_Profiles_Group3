from __future__ import annotations

import logging
import re
import time
from collections.abc import Sequence

from groq import Groq, RateLimitError
from scrapers.config.groq import GroqConfig

logger = logging.getLogger(__name__)

_DURATION_RE = re.compile(r"(\d+(?:\.\d+)?)(ms|s|m|h)")
_MIN_RATE_LIMIT_BACKOFF = 5.0
_MAX_RATE_LIMIT_BACKOFF = 60.0
_CHARS_PER_TOKEN_ESTIMATE = 4
_SAFETY_RATIO = 0.85
# Rotate to the next key in the pool once the current one has been
# rate-limited on more than this many consecutive attempts of the same call.
_MAX_CONSECUTIVE_RATE_LIMITS_BEFORE_ROTATE = 3


def _parse_duration_seconds(value: str | None) -> float:
    """Parse a Go-style duration header ("7m12s", "577ms") or a bare
    retry-after integer/float (plain seconds, no unit suffix) into seconds."""
    if not value:
        return 0.0
    matches = _DURATION_RE.findall(value)
    if matches:
        total = 0.0
        for amount, unit in matches:
            amount = float(amount)
            total += {"ms": amount / 1000, "s": amount, "m": amount * 60, "h": amount * 3600}[unit]
        return total
    try:
        return float(value)
    except ValueError:
        return 0.0


class _FixedWindowRateLimiter:
    """Paces our own outgoing token spend against a per-minute budget.

    Trusting the server's rate-limit headers between calls proved racy - a
    request judged safe by the last response's snapshot could still land
    after the window had already been spent by other traffic, producing a
    sustained burst of 429s. Tracking spend locally, against our own actual
    requests, avoids that race entirely.

    Calls are made one at a time (never concurrently), so there's no need to
    reserve a call's worst-case cost before it runs: gating on tokens already
    spent this window, then crediting each call's *actual* usage afterwards
    via `record`, paces against real consumption instead of a pessimistic
    ceiling. Reserving `max_completion_tokens` (the hard cap, not a typical
    completion size) against every single call previously meant one call's
    estimate alone was often close to the whole per-minute budget, so the
    limiter slept out nearly a full window before every request regardless
    of what that request actually cost.
    """

    def __init__(self, tokens_per_minute: int, safety_ratio: float = _SAFETY_RATIO) -> None:
        self.budget = tokens_per_minute * safety_ratio
        self._window_start = time.monotonic()
        self._used = 0.0

    def wait_for_capacity(self) -> None:
        now = time.monotonic()
        if now - self._window_start >= 60:
            self._window_start = now
            self._used = 0.0
            return
        if self._used >= self.budget:
            sleep_seconds = 60 - (now - self._window_start)
            if sleep_seconds > 0:
                logger.info("Pacing for Groq token budget: sleeping %.1fs.", sleep_seconds)
                time.sleep(sleep_seconds)
            self._window_start = time.monotonic()
            self._used = 0.0

    def record(self, actual_tokens: int) -> None:
        self._used += actual_tokens


class _ApiKeyHub:
    """Rotates through a pool of Groq API keys, each with its own budget.

    Free-tier TPM limits are per-account, so one exhausted key shouldn't
    stall a long batch run when other accounts' keys are available. Each key
    gets its own `_FixedWindowRateLimiter` (its quota is independent of the
    others'), and `rotate()` switches the active key when the caller decides
    the current one is stuck.
    """

    def __init__(self, api_keys: Sequence[str], tokens_per_minute: int) -> None:
        if not api_keys:
            raise RuntimeError("GROQ_API_KEY is not set; required to call the Groq API.")
        self._keys = list(api_keys)
        self._clients = [Groq(api_key=key) for key in self._keys]
        self._limiters = [_FixedWindowRateLimiter(tokens_per_minute) for _ in self._keys]
        self._index = 0

    @property
    def client(self) -> Groq:
        return self._clients[self._index]

    @property
    def limiter(self) -> _FixedWindowRateLimiter:
        return self._limiters[self._index]

    def rotate(self) -> bool:
        """Switch to the next key in the pool. Returns False when there is
        only one key, so the caller falls back to waiting out the current one."""
        if len(self._keys) <= 1:
            return False
        self._index = (self._index + 1) % len(self._keys)
        logger.warning(
            "Rotating to Groq API key %d/%d after repeated rate limits.",
            self._index + 1,
            len(self._keys),
        )
        return True


def build_request_body(config: GroqConfig, prompt: str) -> dict:
    """The chat-completion request body, shared between the synchronous
    GroqCompletion path and Batch API JSONL lines so both submit identical
    requests."""
    return {
        "model": config.model,
        "temperature": config.temperature,
        "reasoning_effort": config.reasoning_effort,
        "max_completion_tokens": config.max_completion_tokens,
        "response_format": {"type": "json_object"},
        "messages": [{"role": "user", "content": prompt}],
    }


class GroqCompletion:
    """Adapter satisfying the `complete(prompt) -> str` contract with a real Groq call.

    Paces requests against the account's token-per-minute limit and retries on
    429s, since a full bronze/silver classification run makes thousands of
    sequential calls over many hours.
    """

    def __init__(self, config: GroqConfig | None = None) -> None:
        self.config = config or GroqConfig()
        self._hub = _ApiKeyHub(self.config.api_keys, self.config.tokens_per_minute_limit)

    def __call__(self, prompt: str) -> str:
        # Fallback only, used to pace this call if Groq doesn't return usage;
        # actual calls are paced by the real usage recorded after they finish.
        estimated_tokens = len(prompt) // _CHARS_PER_TOKEN_ESTIMATE + self.config.max_completion_tokens

        consecutive_rate_limits = 0
        while True:
            self._hub.limiter.wait_for_capacity()
            try:
                raw = self._hub.client.chat.completions.with_raw_response.create(
                    **build_request_body(self.config, prompt)
                )
            except RateLimitError as exc:
                consecutive_rate_limits += 1
                if consecutive_rate_limits > _MAX_CONSECUTIVE_RATE_LIMITS_BEFORE_ROTATE and self._hub.rotate():
                    # Fresh key, fresh (independent) budget - retry right away
                    # instead of sleeping out a backoff computed for the key
                    # we just abandoned.
                    consecutive_rate_limits = 0
                    continue

                # The server's reported reset time can be too small to trust right
                # after a 429 (observed near-0s values that caused a hammering
                # retry loop), so always back off by at least _MIN_RATE_LIMIT_BACKOFF
                # and escalate on consecutive hits rather than retrying instantly.
                reported = _parse_duration_seconds(
                    exc.response.headers.get("x-ratelimit-reset-tokens")
                    or exc.response.headers.get("retry-after")
                )
                escalation = _MIN_RATE_LIMIT_BACKOFF * (2 ** (consecutive_rate_limits - 1))
                wait_seconds = min(max(reported, escalation), _MAX_RATE_LIMIT_BACKOFF)
                logger.warning(
                    "Groq rate limited (attempt %d); sleeping %.1fs before retry.",
                    consecutive_rate_limits,
                    wait_seconds,
                )
                time.sleep(wait_seconds)
                continue

            response = raw.parse()
            usage = response.usage
            self._hub.limiter.record(usage.total_tokens if usage else estimated_tokens)

            content = response.choices[0].message.content
            if not content or not content.strip():
                raise RuntimeError(
                    "Groq returned an empty completion (finish_reason="
                    f"{response.choices[0].finish_reason!r}); the model likely hit "
                    "max_completion_tokens before producing an answer."
                )
            return content
