"""One-off backfill: populate the new location.country column (added by
app/sql/location_country_migration.sql) for every existing row, using the
same rule-based lookup new rows get going forward
(app/utils/country_lookup.py, wired into SilverSync).

Run: python -m scripts.backfill_location_country
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import Location
from app.utils.country_lookup import derive_country

logger = logging.getLogger(__name__)

AUDIT_PATH = Path(__file__).resolve().parent.parent / "evidence" / "backfill_location_country_result.json"


def backfill(db: Session) -> dict:
    locations = db.query(Location).all()
    resolved = 0
    unresolved = []
    for location in locations:
        country = derive_country(location.name)
        location.country = country
        if country is None:
            unresolved.append({"location_id": str(location.location_id), "name": location.name})
        else:
            resolved += 1
    db.flush()
    return {
        "locations_scanned": len(locations),
        "resolved": resolved,
        "unresolved": unresolved,
    }


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    db = SessionLocal()
    try:
        with db.begin():
            summary = backfill(db)
            AUDIT_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info(
            "Backfill complete: %d/%d locations resolved a country, %d left NULL (no textual signal). Audit: %s",
            summary["resolved"], summary["locations_scanned"], len(summary["unresolved"]), AUDIT_PATH,
        )
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
