from collections import defaultdict, deque
from threading import Lock
from time import monotonic


class LoginRateLimiter:
    """Process-local limiter for development and single-worker deployments.

    Production deployments with multiple workers or application instances must
    replace this with a shared-store implementation, such as Redis, so every
    process observes the same failed-login counters.
    """

    def __init__(self, max_attempts: int, window_seconds: int):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._attempts: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def _remove_expired(self, attempts: deque[float], now: float) -> None:
        cutoff = now - self.window_seconds
        while attempts and attempts[0] <= cutoff:
            attempts.popleft()

    def retry_after(self, key: str) -> int | None:
        now = monotonic()
        with self._lock:
            attempts = self._attempts[key]
            self._remove_expired(attempts, now)
            if len(attempts) < self.max_attempts:
                return None
            return max(1, int(attempts[0] + self.window_seconds - now) + 1)

    def record_failure(self, key: str) -> None:
        now = monotonic()
        with self._lock:
            attempts = self._attempts[key]
            self._remove_expired(attempts, now)
            attempts.append(now)

    def clear(self, key: str) -> None:
        with self._lock:
            self._attempts.pop(key, None)

    def reset(self) -> None:
        with self._lock:
            self._attempts.clear()
