"""Vercel Python entrypoint for the FastAPI backend.

backend/app/*.py all import as `from app.core... import ...`, which only
resolves when backend/ itself (not backend/app/) is on sys.path - the same
requirement backend/conftest.py sets up for pytest and Docker's WORKDIR /app
satisfies by having the app/ package live directly under the working
directory. Vercel's Python runtime puts this file's own directory on
sys.path, not backend/, so that import would fail without this shim.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.main import app  # noqa: E402
