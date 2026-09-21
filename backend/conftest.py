"""Makes `app` (and `scripts`) importable as top-level packages, and loads
backend/.env, regardless of which directory pytest is invoked from.

backend/tests/*.py do `from app...` / `from scripts...`, which only resolves
when `backend/` itself is on sys.path. Running pytest from the repo root
normally leaves `backend/` off sys.path (Python only adds the invocation
cwd), causing `ModuleNotFoundError: No module named 'app'` at conftest load
time. pytest always discovers and imports every conftest.py between rootdir
and a collected test file, so this one loads before backend/tests/conftest.py
even when invoked as `python -m pytest backend/tests` from the repo root.

app/core/config.py also calls `load_dotenv()` with no path, which searches
upward from the current working directory - it only finds backend/.env when
cwd is backend/ itself. Loading it here by absolute path first makes that
lookup (and anything it sets, e.g. a local ENVIRONMENT=development) behave
the same regardless of invocation directory, matching today's cwd=backend/
behavior rather than changing it.
"""

import sys
from pathlib import Path

from dotenv import load_dotenv

_BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_BACKEND_DIR))
load_dotenv(_BACKEND_DIR / ".env")
