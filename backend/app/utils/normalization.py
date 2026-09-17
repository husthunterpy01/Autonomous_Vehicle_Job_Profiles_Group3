"""Shared text normalization; callers choose the identity contract."""


def normalized(value: str) -> str:
    return " ".join(value.split()).lower()
