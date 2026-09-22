"""Version 1 imports producer labels; it does not infer a taxonomy or AV status."""
import unicodedata
from pathlib import Path

import yaml

from app.models import Category
from app.services.job_identity import resolve_job

_MAIN_TYPES_PATH = Path(__file__).resolve().parent.parent / "config" / "category_main_types.yaml"


def _normalize_text(value):
    return " ".join(unicodedata.normalize("NFKC", value).split())


def _load_main_types_by_normalized_name(path):
    """main_type is a property of the category, not of any individual job -
    load the static sub_type -> main_type mapping once here rather than
    trusting a per-record value from the handoff, which let two disagreeing
    records silently flip a shared Category row (last-writer-wins)."""
    if not path.is_file():
        return {}
    with path.open("r", encoding="utf-8") as stream:
        mapping = yaml.safe_load(stream) or {}
    return {_normalize_text(sub_type).casefold(): main_type for sub_type, main_type in mapping.items()}


_MAIN_TYPES_BY_NORMALIZED_NAME = _load_main_types_by_normalized_name(_MAIN_TYPES_PATH)


def _normalize_text(value):
    return " ".join(unicodedata.normalize("NFKC", value).split())


def category_labels(row):
    """Returns (version, {normalized_name: display_sub_type}).

    Each entry in `functional_area` is a plain string; main_type is never
    supplied per-record (see _MAIN_TYPES_BY_NORMALIZED_NAME).
    """
    version = row.get("taxonomy_version", 1)
    if type(version) is not int or version < 1:
        raise ValueError("taxonomy_version must be a positive integer")
    labels = row["functional_area"]
    if isinstance(labels, str):
        labels = [labels]
    if not isinstance(labels, list):
        raise TypeError("functional_area must be a string or an array of strings; use [] to clear")
    canonical = {}
    for label in labels:
        if not isinstance(label, str):
            raise TypeError("Category labels must be strings")
        display = _normalize_text(label)
        if not display:
            raise ValueError("Category labels must be non-empty strings")
        canonical.setdefault(display.casefold(), display)
    return version, canonical


def dominant_categories(categories: list[Category]) -> list[Category]:
    """A job gets exactly one main_type, though it may carry several
    sub_types that share it: group by (taxonomy_version, main_type) and
    keep only the largest group, dropping the rest. Without this, a job
    whose functional_area spans two main_types (e.g. Perception and
    Planning) would link to both in job_category - the filter in
    app/services/job.py:list_jobs checks that raw link table directly, so
    it would match a category the response never shows (job.py's
    _to_category_response already collapses to one group for display),
    letting a user filter by a category whose job doesn't visibly have it.
    Enforcing the same collapse here, at write time, keeps every reader
    (filter and response alike) consistent by construction.

    Does not sort `categories` before grouping - sync_categories passes
    them in the order functional_area listed them (the classifier's own
    order), and on a tie this keeps whichever group's first sub_type the
    classifier listed earliest, mirroring scrapers/service/llm/
    category_hierarchy.constrain_to_dominant_main_type's tie-break. An
    earlier version sorted by normalized_name here, which silently
    replaced that signal with alphabetical order - discarding real
    classifier output on every tie for a naming coincidence.
    """
    groups: dict[tuple[int, str | None], list[Category]] = {}
    for category in categories:
        key = (category.taxonomy_version, category.main_type)
        groups.setdefault(key, []).append(category)
    if not groups:
        return []
    _, members = max(groups.items(), key=lambda item: len(item[1]))
    return members


def _preload_categories(db, keys: set[tuple[int, str]]) -> dict[tuple[int, str], Category]:
    """One query per distinct taxonomy_version touched by this batch,
    instead of one SELECT per label per job (~15-40k round-trips on a full
    import). The taxonomy is small (a handful of versions, ~9 categories
    each), so fetching every category for the relevant version(s) is cheap
    and lets every sync_categories call in the batch reuse this dict."""
    versions = {version for version, _ in keys}
    if not versions:
        return {}
    rows = db.query(Category).filter(Category.taxonomy_version.in_(versions)).all()
    return {(c.taxonomy_version, c.normalized_name): c for c in rows}


def _collect_category_keys(records) -> set[tuple[int, str]]:
    """Best-effort scan to size the preload query - a row with malformed
    functional_area just contributes nothing here; the real validation and
    error message still happen per-row in import_categories's own loop."""
    keys = set()
    for row in records:
        if not isinstance(row, dict) or "functional_area" not in row:
            continue
        try:
            version, labels = category_labels(row)
        except (TypeError, ValueError):
            continue
        keys.update((version, normalized) for normalized in labels)
    return keys


def sync_categories(db, job, row, cache: dict | None = None):
    if "functional_area" not in row:
        return
    version, labels = category_labels(row)
    if cache is None:
        cache = _preload_categories(db, {(version, normalized) for normalized in labels})
    linked = []
    for normalized, display in labels.items():
        key = (version, normalized)
        category = cache.get(key)
        static_main_type = _MAIN_TYPES_BY_NORMALIZED_NAME.get(normalized)
        if category is None:
            category = Category(sub_type=display, normalized_name=normalized, taxonomy_version=version, main_type=static_main_type)
            db.add(category)
            db.flush()
            cache[key] = category
        elif static_main_type and category.main_type != static_main_type:
            category.main_type = static_main_type
        linked.append(category)
    job.categories = dominant_categories(linked)
    db.flush()


def import_categories(db, records):
    """Caller owns transaction and writer serialization, as for SilverSync."""
    if not isinstance(records, list):
        raise TypeError("Handoff must be a JSON array")
    cache = _preload_categories(db, _collect_category_keys(records))
    seen = set()
    updated = 0
    for index, row in enumerate(records):
        try:
            if not isinstance(row, dict):
                raise TypeError("Each record must be an object")
            job = resolve_job(db, row)
            if job.job_id in seen:
                raise ValueError("Multiple handoff records target the same backend job")
            seen.add(job.job_id)
            sync_categories(db, job, row, cache=cache)
            updated += int("functional_area" in row)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Row {index + 1}: {exc}") from exc
    return {"read": len(records), "updated": updated}
