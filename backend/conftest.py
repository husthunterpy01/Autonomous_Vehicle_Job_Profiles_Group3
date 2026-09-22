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

DATABASE_URL is force-overridden after that load, unlike everything else
.env sets. app/core/database.py's module-level `engine` is bound to it at
import time and create_engine() is lazy - it never actually connects until
something executes a query through it - so nothing breaks today (every test
either uses the in-memory SQLite db_session fixture or mocks `engine`
directly). But nothing stops a future test from doing neither, and if a
developer's local .env points DATABASE_URL at a shared/Supabase database (a
plausible local dev setup), that test would silently reach it. Forcing an
in-memory sqlite URL here makes that impossible regardless of .env content.
One opt-in test (test_be9_postgres_migration.py, gated behind
BE9_TEST_POSTGRES=1) falls back to DATABASE_URL when BE9_TEST_DATABASE_URL
isn't set - that fallback stops working, and BE9_TEST_DATABASE_URL must be
set explicitly. That's intentional: a deliberately-dangerous opt-in test
should not depend on a general-purpose var for which database it touches.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

_BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_BACKEND_DIR))
load_dotenv(_BACKEND_DIR / ".env")
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
