"""Read-only validation of external classification handoff records."""
from app.services.category_sync import category_labels
from app.services.job_identity import resolve_job


def validate_records(db, records):
    if not isinstance(records, list):
        raise TypeError("Handoff must be a JSON array")
    results = []
    seen = set()
    for index, row in enumerate(records):
        try:
            if not isinstance(row, dict):
                raise TypeError("Each record must be an object")
            job = resolve_job(db, row)
            if job.job_id in seen:
                raise ValueError("Multiple handoff records target the same backend job")
            seen.add(job.job_id)
            if "functional_area" in row:
                category_labels(row)
            results.append({
                "row": index + 1,
                "backend_job_id": str(job.job_id),
                "source_key": job.source_key,
                "category_status": "ready_to_import" if "functional_area" in row else "not_provided",
            })
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Row {index + 1}: {exc}") from exc
    return {"matched": len(results), "writes": 0, "items": results}


