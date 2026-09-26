"""Fail if api/requirements.txt has drifted from backend/requirements.txt.

Vercel's Python requirements parser rejects pip's `-r <file>` include, so
api/requirements.txt is a hand-maintained copy of the backend's runtime
dependencies (everything except pytest, which the deployed app never
imports). Without this check, bumping or adding a package in
backend/requirements.txt would leave the Vercel deployment on stale pins.

Run from the repo root: python .github/scripts/check_api_requirements.py
"""
import sys
from pathlib import Path

API = Path("api/requirements.txt")
BACKEND = Path("backend/requirements.txt")
TEST_ONLY = ("pytest",)


def requirements(path: Path, skip_test_only: bool = False) -> set[str]:
    found = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        if skip_test_only and line.lower().startswith(TEST_ONLY):
            continue
        found.add(line.lower())
    return found


def main() -> int:
    api = requirements(API)
    backend = requirements(BACKEND, skip_test_only=True)
    if api == backend:
        print(f"OK: {API} matches {BACKEND} ({len(api)} packages, test-only excluded).")
        return 0
    print(f"ERROR: {API} is out of sync with {BACKEND}.")
    for name in sorted(backend - api):
        print(f"  missing from {API}: {name}")
    for name in sorted(api - backend):
        print(f"  only in {API}:      {name}")
    print(f"Update {API} to mirror the runtime packages in {BACKEND} (minus pytest).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
