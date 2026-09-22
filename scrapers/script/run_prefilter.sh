#!/usr/bin/env bash
# Runs the deterministic AV pre-filter over a Silver export (or any CSV/
# JSON/JSONL of job postings), before anything goes to an LLM. Same as
# `python3 -m scrapers.utils.job_prefilter`.
#
# Usage:
#   scrapers/script/run_prefilter.sh --input data/silver_export.jsonl --output-dir data/job_prefilter
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

if [[ -z "${VIRTUAL_ENV:-}" && -f ".venv/bin/activate" ]]; then
    # shellcheck disable=SC1091
    source ".venv/bin/activate"
fi

exec python3 -m scrapers.utils.job_prefilter "$@"
