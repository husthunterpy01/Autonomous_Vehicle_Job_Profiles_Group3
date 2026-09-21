#!/usr/bin/env bash
# Exports silver.cleaned_job_postings to a JSONL file - the handoff point
# between the dbt-managed Silver table and the file-based pre-filter/
# classify/enrich stages. Same as
# `python3 -m scrapers.service.silver_cleaning.silver_export`.
#
# Usage:
#   scrapers/script/run_silver_export.sh                             # writes data/silver_export.jsonl
#   scrapers/script/run_silver_export.sh --output data/silver_export.jsonl
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

if [[ -z "${VIRTUAL_ENV:-}" && -f ".venv/bin/activate" ]]; then
    # shellcheck disable=SC1091
    source ".venv/bin/activate"
fi

exec python3 -m scrapers.service.silver_cleaning.silver_export "$@"
