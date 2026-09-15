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
# A transient per-minute limit clears within a couple of these 60s-capped
# sleeps. A block that's still there after 15 minutes on the last available
# key is a daily/quota-type 429 that won't clear soon - raise instead of
# retrying forever and hanging the pipeline stage (see GroqCompletion).
_MAX_TOTAL_RATE_LIMIT_WAIT = 900.0
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

    Calls are made one at a time (never concurrently), so a cheap estimate
    reserved before each call - not the call's worst-case cost - is enough to
    know whether it fits this window; `reconcile` then corrects that estimate
    to the call's *actual* usage once the response comes back, so a
    systematically-off estimate self-corrects instead of drifting. Reserving
    `max_completion_tokens` (the hard cap, not a typical completion size)
    against every single call was the old bug: that estimate alone was often
    close to the whole per-minute budget, so the limiter slept out nearly a
    full window before every request regardless of what it actually cost.
    Reserving nothing at all, the fix that replaced it, went too far the
    other way: a call admitted with only a little headroom left could still
    overshoot the budget once its real cost landed, and a 429 from that
    overshoot was never charged against the window at all (the call had
    nothing reserved to begin with), so the same overshoot could repeat
    immediately. Reserving a right-sized estimate and reconciling it keeps
    both fixed.
    """

    def __init__(self, tokens_per_minute: int, safety_ratio: float = _SAFETY_RATIO) -> None:
        self.budget = tokens_per_minute * safety_ratio
        self._window_start = time.monotonic()
        self._used = 0.0

    def wait_for_capacity(self, reserved_tokens: float = 0.0) -> None:
        """Block until `reserved_tokens` fits the current window, then commit
        that reservation immediately - before the call it's for even runs -
        so the next call's admission check already sees it as spent instead
        of judging capacity as if this call cost nothing."""
        now = time.monotonic()
        if now - self._window_start >= 60:
            self._window_start = now
            self._used = 0.0
        elif self._used + reserved_tokens >= self.budget:
            sleep_seconds = 60 - (now - self._window_start)
            if sleep_seconds > 0:
                logger.info("Pacing for Groq token budget: sleeping %.1fs.", sleep_seconds)
                time.sleep(sleep_seconds)
            self._window_start = time.monotonic()
            self._used = 0.0
        self._used += reserved_tokens

    def reconcile(self, reserved_tokens: float, actual_tokens: float) -> None:
        self._used += actual_tokens - reserved_tokens


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
        # Running mean of real completion_tokens across every call this
        # instance has made, used to size the pre-call reservation below
        # instead of the pessimistic max_completion_tokens ceiling. Starts at
        # 0 (no data yet) rather than a conservative seed: an under-reserved
        # first call is reconciled to its real cost right after it returns,
        # so the only cost of starting at 0 is one call's admission decision
        # being slightly optimistic - not the repeated, per-call
        # over-reservation this was built to avoid.
        self._avg_completion_tokens = 0.0
        self._completion_samples = 0

    def _record_completion_tokens(self, tokens: int) -> None:
        self._completion_samples += 1
        self._avg_completion_tokens += (tokens - self._avg_completion_tokens) / self._completion_samples

    def __call__(self, prompt: str) -> str:
        # Cheap pre-call estimate (not a worst-case ceiling) so admission is
        # gated on roughly what this call will cost, not just on tokens
        # already spent; reconciled against real usage.total_tokens below.
        reserved_tokens = len(prompt) / _CHARS_PER_TOKEN_ESTIMATE + self._avg_completion_tokens
        # Fallback only, for reconciling this call if Groq doesn't return
        # usage at all; every other call is reconciled from real usage.
        estimated_tokens = len(prompt) // _CHARS_PER_TOKEN_ESTIMATE + self.config.max_completion_tokens

        consecutive_rate_limits = 0
        total_rate_limit_wait = 0.0
        reserved_on_active_key = False
        while True:
            if not reserved_on_active_key:
                self._hub.limiter.wait_for_capacity(reserved_tokens)
                reserved_on_active_key = True
            try:
                raw = self._hub.client.chat.completions.with_raw_response.create(
                    **build_request_body(self.config, prompt)
                )
            except RateLimitError as exc:
                consecutive_rate_limits += 1
                if consecutive_rate_limits > _MAX_CONSECUTIVE_RATE_LIMITS_BEFORE_ROTATE and self._hub.rotate():
                    # Fresh key, fresh (independent) budget - retry right away
                    # instead of sleeping out a backoff computed for the key
                    # we just abandoned, reset the wait clock since it was
                    # tracking the abandoned key's block, not this one's, and
                    # reserve this call's estimate against the new key too.
                    consecutive_rate_limits = 0
                    total_rate_limit_wait = 0.0
                    reserved_on_active_key = False
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

                total_rate_limit_wait += wait_seconds
                if total_rate_limit_wait > _MAX_TOTAL_RATE_LIMIT_WAIT:
                    raise RuntimeError(
                        f"Groq rate limited for over {_MAX_TOTAL_RATE_LIMIT_WAIT:.0f}s straight "
                        f"({consecutive_rate_limits} attempts) on the last available key; this "
                        "looks like a quota exhaustion that won't clear soon rather than a "
                        "transient per-minute limit, so failing instead of retrying forever."
                    ) from exc

                logger.warning(
                    "Groq rate limited (attempt %d); sleeping %.1fs before retry.",
                    consecutive_rate_limits,
                    wait_seconds,
                )
                time.sleep(wait_seconds)
                continue

            response = raw.parse()
            usage = response.usage
            self._hub.limiter.reconcile(reserved_tokens, usage.total_tokens if usage else estimated_tokens)
            if usage:
                self._record_completion_tokens(usage.completion_tokens)

            content = response.choices[0].message.content
            if not content or not content.strip():
                raise RuntimeError(
                    "Groq returned an empty completion (finish_reason="
                    f"{response.choices[0].finish_reason!r}); the model likely hit "
                    "max_completion_tokens before producing an answer."
                )
            return content
