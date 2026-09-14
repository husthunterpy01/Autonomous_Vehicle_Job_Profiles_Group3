import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()
load_dotenv("./scrapers/.env")


@dataclass(frozen=True)
class GroqConfig:
    # One or more comma-separated keys, tried in order; a key after the
    # first is only used once every key before it has been rate-limited on
    # more than 3 consecutive attempts (see _ApiKeyHub in groq_client.py).
    api_key: str = os.environ.get("GROQ_API_KEY", "")
    api_keys: tuple[str, ...] = ()
    model: str = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")
    temperature: float = float(os.environ.get("GROQ_TEMPERATURE", "0"))
    # gpt-oss models spend part of the completion budget on hidden reasoning
    # tokens before the JSON answer; "low" keeps that from crowding out the
    # answer on long job descriptions, which otherwise come back empty.
    reasoning_effort: str = os.environ.get("GROQ_REASONING_EFFORT", "low")
    max_completion_tokens: int = int(os.environ.get("GROQ_MAX_COMPLETION_TOKENS", "4096"))
    # Measured empirically for this account/model (x-ratelimit-limit-tokens).
    # Client-side pacing is computed from this rather than trusted from
    # per-response headers, which proved too racy under back-to-back calls.
    tokens_per_minute_limit: int = int(os.environ.get("GROQ_TPM_LIMIT", "8000"))

    def __post_init__(self) -> None:
        if self.api_keys:
            return
        keys = tuple(k.strip() for k in self.api_key.split(",") if k.strip())
        object.__setattr__(self, "api_keys", tuple(dict.fromkeys(keys)))
