from __future__ import annotations

from pathlib import Path

import yaml

DEFAULT_MAIN_TYPES_PATH = Path(__file__).resolve().parents[2] / "config" / "category_main_types.yaml"


def load_main_types(path: Path = DEFAULT_MAIN_TYPES_PATH) -> dict[str, str]:
    """The static sub_type -> main_type mapping (see CategoryTaxonomyExtractor
    for how it was derived) - frozen into this file rather than recomputed
    per job so every job's category assignment stays consistent."""
    with path.open("r", encoding="utf-8") as stream:
        mapping = yaml.safe_load(stream) or {}
    if not isinstance(mapping, dict):
        raise ValueError(f"{path} must be a YAML mapping of sub_type -> main_type")  # noqa: TRY004 - malformed YAML, not a Python type error
    return mapping


def constrain_to_dominant_main_type(
    categories: tuple[str, ...], main_types: dict[str, str] | None = None
) -> tuple[str, ...]:
    """Each job gets exactly one main_type but may keep multiple sub_types
    under it: group the raw (possibly cross-main_type) matches by main_type,
    keep only the group with the most matches, and drop the rest. Ties keep
    whichever group's first sub_type appeared earliest in `categories`,
    since dict insertion order tracks that and max() returns the first
    maximal element on a tie.

    An unrecognized sub_type (missing from the mapping) is treated as its
    own singleton group rather than dropped silently or crashing, so a stale
    mapping fails soft instead of erasing an otherwise-valid category.
    """
    if main_types is None:
        main_types = load_main_types()
    groups: dict[str, list[str]] = {}
    for category in categories:
        group = main_types.get(category, category)
        groups.setdefault(group, []).append(category)
    if not groups:
        return ()
    dominant = max(groups, key=lambda group: len(groups[group]))
    return tuple(groups[dominant])
