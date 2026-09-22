class ProviderRateLimitExhausted(RuntimeError):
    """Every key in this provider config's pool is rate-limited for this call.

    Wrappers (gpt-oss-20b -> gpt-oss-120b on Groq) catch this and switch.
    """
