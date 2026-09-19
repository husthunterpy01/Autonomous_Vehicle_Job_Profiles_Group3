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
    categories: tuple[str, ...],
    main_types: dict[str, str] | None = None,
    weights: dict[str, int] | None = None,
) -> tuple[str, ...]:
    """Each job gets exactly one main_type but may keep multiple sub_types
    under it: group the raw (possibly cross-main_type) matches by main_type,
    keep only the strongest group, and drop the rest.

    `weights` lets a caller with a real per-category signal (e.g.
    KeywordCategoryClassifier's distinct-keyword-match count, or the LLM's
    own reported confidence) rank groups by more than just how many
    sub_types matched. A group is ranked first by its single
    *highest*-weighted category, then (only to break a tie on that) by the
    group's total weight:

    - Highest-weighted-category first, not summed, because summing let
      several weakly-evidenced categories in one group outrank one
      strongly-evidenced category in another (e.g. two Medium-confidence
      categories beating one High-confidence category) - quantity of weak
      guesses shouldn't out-vote one strong signal.
    - Total weight as the tie-break (not category count, and not silently
      dropped) because it's what let a group with two *equally*-confident
      sub_types correctly outrank a group with only one, before this
      weights feature existed - collapsing straight to response-order on
      that tie would have thrown away that behavior for the common case of
      uniform confidence (or the default, no-weights-supplied path, which
      needs it too, since every category is weight 1 there).

    Omit `weights` (as the LLM path did before it started reporting
    confidence) to fall back to a weight of 1 per category, i.e. group size
    for both the primary and tie-break comparisons.

    A true tie on both keeps whichever group's first sub_type appeared
    earliest in `categories`, since dict insertion order tracks that and
    max() returns the first maximal element on a tie.

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
    weights = weights or {}

    def _score(group: str) -> tuple[int, int]:
        group_weights = [weights.get(c, 1) for c in groups[group]]
        return (max(group_weights), sum(group_weights))

    dominant = max(groups, key=_score)
    return tuple(groups[dominant])
