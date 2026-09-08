"""Read-only identity preflight: python -m app.validate_handoff handoff.json."""
import argparse
import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.database import engine
from app.services.job_identity import resolve_job
from app.services.category_sync import category_labels


def validate_records(db, records):
    if not isinstance(records, list):
        raise ValueError("Handoff must be a JSON array")
    results = []
    seen = set()
    for index, row in enumerate(records):
        try:
            if not isinstance(row, dict):
                raise ValueError("Each record must be an object")
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
        except ValueError as exc:
            raise ValueError(f"Row {index + 1}: {exc}") from exc
    return {"matched": len(results), "writes": 0, "items": results}


def main():
    parser = argparse.ArgumentParser(description="Validate external job identities without writing data")
    parser.add_argument("input", type=Path, help="JSON array containing explicit Silver/source identities")
    args = parser.parse_args()
    try:
        records = json.loads(args.input.read_text(encoding="utf-8-sig"))
        with Session(engine) as db:
            report = validate_records(db, records)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
