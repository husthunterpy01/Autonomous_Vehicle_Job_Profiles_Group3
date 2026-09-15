from __future__ import annotations

import html
import json
import re


def normalize_text(value: object) -> str:
    """Strip HTML/JSON noise from a raw scraped field down to plain text."""
    if value is None:
        return ""
    if isinstance(value, (dict, list, tuple)):
        value = json.dumps(value, ensure_ascii=False, default=str)
    plain_text = re.sub(r"<[^>]+>", " ", html.unescape(str(value)))
    return re.sub(r"\s+", " ", plain_text).strip()


# Section headers that reliably mark the end of a posting's technical content
# and the start of boilerplate (benefits, legal, how-to-apply) that carries no
# AV-relevance/category/skill signal. Cutting here before a hard length cap
# means truncation drops filler first instead of slicing off requirements
# text that happened to land past the character limit.
_BOILERPLATE_MARKERS = re.compile(
    r"\b("
    r"benefits|compensation|salary range|pay range|pay transparency|"
    r"what we offer|perks|equal opportunity|eeo statement|"
    r"accommodations?|how to apply|about the company|about us"
    r")\b",
    re.IGNORECASE,
)


def compress_job_text(title: str, description: str, max_chars: int) -> tuple[str, str]:
    """Normalize title/description and cut description boilerplate before a
    hard length cap, so truncation loses filler before it loses substance."""
    title = normalize_text(title)
    description = normalize_text(description)

    # Only trust a boilerplate marker once a reasonable amount of technical
    # content has already been seen; some postings open with "About us".
    match = _BOILERPLATE_MARKERS.search(description, pos=min(len(description), 200))
    if match:
        description = description[: match.start()].rstrip()

    return title, description[:max_chars]
