"""Manual transactional import: python -m app.import_categories handoff.json."""
import argparse
import json
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import engine
from app.services.category_sync import import_categories


def main():
    parser = argparse.ArgumentParser(description="Import functional_area labels into backend categories")
    parser.add_argument("input", type=Path)
    args = parser.parse_args()
    try:
        records = json.loads(args.input.read_text(encoding="utf-8-sig"))
        with Session(engine) as db, db.begin():
            if engine.dialect.name == "postgresql":
                db.execute(text("SELECT pg_advisory_xact_lock(80009001)"))
            counts = import_categories(db, records)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(counts))


if __name__ == "__main__":
    main()
