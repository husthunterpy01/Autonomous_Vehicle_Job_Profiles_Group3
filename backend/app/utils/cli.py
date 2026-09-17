"""Shared argument parsing, JSON input and error reporting for backend commands."""
import argparse
import json
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
