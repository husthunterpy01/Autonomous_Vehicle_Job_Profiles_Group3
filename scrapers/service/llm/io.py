from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


class JobPostingIO:
    @staticmethod
    def load(path: str | Path) -> list[dict[str, Any]]:
        """Load a Bronze/Silver CSV, JSON array, or JSON Lines export."""
        input_path = Path(path)
        suffix = input_path.suffix.lower()
        if suffix == ".csv":
            with input_path.open("r", encoding="utf-8-sig", newline="") as stream:
                return [dict(row) for row in csv.DictReader(stream)]

        with input_path.open("r", encoding="utf-8") as stream:
            if suffix == ".jsonl":
                return [json.loads(line) for line in stream if line.strip()]
            payload = json.load(stream)

        if not isinstance(payload, list) or not all(
            isinstance(row, dict) for row in payload
        ):
            raise ValueError("JSON input must contain an array of job objects")
        return payload

    @classmethod
    def write_json_lines(
        cls, path: Path, rows: Iterable[Mapping[str, Any]]
    ) -> None:
        with path.open("w", encoding="utf-8") as stream:
            for row in rows:
                stream.write(
                    json.dumps(
                        cls.json_safe(row),
                        ensure_ascii=False,
                        default=str,
                        allow_nan=False,
                    )
                    + "\n"
                )

    @staticmethod
    def write_json(path: Path, value: Any) -> None:
        path.write_text(
            json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def write_csv(
        path: Path, rows: Sequence[Mapping[str, Any]], fieldnames: Sequence[str]
    ) -> None:
        with path.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    @classmethod
    def json_safe(cls, value: Any) -> Any:
        if isinstance(value, float) and not math.isfinite(value):
            return None
        if isinstance(value, Mapping):
            return {key: cls.json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [cls.json_safe(item) for item in value]
        return value
