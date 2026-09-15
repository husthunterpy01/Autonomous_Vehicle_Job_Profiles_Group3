from __future__ import annotations


def strip_code_fence(text: str) -> str:
    """Strip a ```json ... ``` or ``` ... ``` fence an LLM sometimes wraps JSON in."""
    text = text.strip()
    if not text.startswith("```"):
        return text
    lines = text.splitlines()
    text = "\n".join(lines[1:-1])
    if text.lstrip().startswith("json"):
        text = text.lstrip()[4:].lstrip()
    return text


def parse_string_list(value: object) -> tuple[str, ...]:
    """Validate a JSON array of strings and dedupe it, preserving order."""
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError("Expected a JSON array of strings")
    seen: set[str] = set()
    deduped: list[str] = []
    for item in value:
        stripped = item.strip()
        if stripped and stripped not in seen:
            deduped.append(stripped)
            seen.add(stripped)
    return tuple(deduped)
