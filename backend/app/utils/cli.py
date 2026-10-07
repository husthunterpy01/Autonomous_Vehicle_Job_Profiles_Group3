"""Shared argument parsing, JSON input and error reporting for backend commands."""
import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path


def input_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("input", type=Path, help="Path to a JSON handoff array")
    return parser


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def run_command(parser, operation):
    args = parser.parse_args()
    try:
        result = operation(args)
    except (OSError, TypeError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2))


def mirror_to_supabase(sync: Callable[..., bool]) -> None:
    """Mirror to Supabase after a local write; exit non-zero if the mirror fails.

    The local write is already committed when this runs, so the summary has been
    printed. Skipping because Supabase is not configured is not a failure.
    """
    try:
        sync(required=True)
    except RuntimeError as exc:
        print(f"{exc}\nThe local write succeeded. Re-run: python -m scripts.sync_to_supabase", file=sys.stderr)
        raise SystemExit(1) from exc

