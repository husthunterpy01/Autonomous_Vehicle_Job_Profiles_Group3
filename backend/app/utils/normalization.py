"""Shared text normalization; callers choose the identity contract."""
import re

# Page furniture some career sites put in a location field.
_LOCATION_LABEL_PREFIX = re.compile(r"^\s*location\s*:\s*", re.IGNORECASE)
_LOCATION_MORE_SUFFIX = re.compile(r"\s*\+\s*\d+\s*more\s*$", re.IGNORECASE)


def normalized(value: str) -> str:
    return " ".join(value.split()).lower()


def clean_location_name(value: str) -> str:
    """A location name without a leading "Location:" label or a trailing
    "+2 more" count, with whitespace collapsed; "" when nothing is left."""
    value = _LOCATION_MORE_SUFFIX.sub("", _LOCATION_LABEL_PREFIX.sub("", value))
    return " ".join(value.split())
