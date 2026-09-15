"""Version 1 imports producer labels; it does not infer a taxonomy or AV status."""
import unicodedata

from app.models import Category
from app.services.job_identity import resolve_job


def _normalize_text(value):
    return " ".join(unicodedata.normalize("NFKC", value).split())


def category_labels(row):
    """Returns (version, {normalized_name: (display_sub_type, main_type_or_None)}).

    Each entry in `functional_area` is either a plain string (sub_type only;
    main_type is not touched) or an object {"sub_type": ..., "main_type": ...}
    - main_type is a property of the category itself (one Category row per
    (taxonomy_version, sub_type), not per job), so it's optional per label
    rather than required on every record.
    """
    version = row.get("taxonomy_version", 1)
    if type(version) is not int or version < 1:
        raise ValueError("taxonomy_version must be a positive integer")
    labels = row["functional_area"]
    if isinstance(labels, str):
        labels = [labels]
    if not isinstance(labels, list):
        raise TypeError("functional_area must be a string, an object, or an array; use [] to clear")
    canonical = {}
    for label in labels:
        if isinstance(label, str):
            sub_type, main_type = label, None
        elif isinstance(label, dict):
            sub_type = label.get("sub_type")
            if not isinstance(sub_type, str):
                raise TypeError("Category label objects require a string sub_type")
            main_type = label.get("main_type")
            if main_type is not None and not isinstance(main_type, str):
                raise TypeError("main_type must be a string when provided")
        else:
            raise TypeError("Category labels must be strings or {sub_type, main_type} objects")
        display = _normalize_text(sub_type)
        if not display:
            raise ValueError("Category labels must be non-empty strings")
        main_type = _normalize_text(main_type) or None if main_type else None
        canonical.setdefault(display.casefold(), (display, main_type))
    return version, canonical


def sync_categories(db, job, row):
    if "functional_area" not in row:
        return
    version, labels = category_labels(row)
    linked = []
    for normalized, (display, main_type) in labels.items():
        category = db.query(Category).filter_by(taxonomy_version=version, normalized_name=normalized).one_or_none()
        if category is None:
            category = Category(sub_type=display, normalized_name=normalized, taxonomy_version=version, main_type=main_type)
            db.add(category)
            db.flush()
        elif main_type and category.main_type != main_type:
            category.main_type = main_type
        linked.append(category)
    job.categories = linked
    db.flush()


def import_categories(db, records):
    """Caller owns transaction and writer serialization, as for SilverSync."""
    if not isinstance(records, list):
        raise TypeError("Handoff must be a JSON array")
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
            sync_categories(db, job, row)
            updated += int("functional_area" in row)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Row {index + 1}: {exc}") from exc
    return {"read": len(records), "updated": updated}
