"""Version 1 imports producer labels; it does not infer a taxonomy or AV status."""
import unicodedata

from app.models import Category
from app.services.job_identity import resolve_job


def category_labels(row):
    version = row.get("taxonomy_version", 1)
    if type(version) is not int or version < 1:
        raise ValueError("taxonomy_version must be a positive integer")
    labels = row["functional_area"]
    if isinstance(labels, str):
        labels = [labels]
    if not isinstance(labels, list):
        raise ValueError("functional_area must be a string or an array; use [] to clear")
    canonical = {}
    for label in labels:
        if not isinstance(label, str):
            raise ValueError("Category labels must be non-empty strings")
        display = " ".join(unicodedata.normalize("NFKC", label).split())
        if not display:
            raise ValueError("Category labels must be non-empty strings")
        canonical.setdefault(display.casefold(), display)
    return version, canonical


def sync_categories(db, job, row):
    if "functional_area" not in row:
        return
    version, labels = category_labels(row)
    linked = []
    for normalized, display in labels.items():
        category = db.query(Category).filter_by(taxonomy_version=version, normalized_name=normalized).one_or_none()
        if category is None:
            category = Category(sub_type=display, normalized_name=normalized, taxonomy_version=version)
            db.add(category)
            db.flush()
        linked.append(category)
    job.categories = linked
    db.flush()


def import_categories(db, records):
    """Caller owns transaction and writer serialization, as for SilverSync."""
    if not isinstance(records, list):
        raise ValueError("Handoff must be a JSON array")
    seen = set()
    updated = 0
    for index, row in enumerate(records):
        try:
            if not isinstance(row, dict):
                raise ValueError("Each record must be an object")
            job = resolve_job(db, row)
            if job.job_id in seen:
                raise ValueError("Multiple handoff records target the same backend job")
            seen.add(job.job_id)
            sync_categories(db, job, row)
            updated += int("functional_area" in row)
        except ValueError as exc:
            raise ValueError(f"Row {index + 1}: {exc}") from exc
    return {"read": len(records), "updated": updated}
