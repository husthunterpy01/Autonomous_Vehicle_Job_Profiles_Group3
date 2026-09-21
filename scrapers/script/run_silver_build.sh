#!/usr/bin/env bash
# Builds the dbt Silver model (silver.cleaned_job_postings) from whatever is
# currently in bronze.job_postings. Same as
# `python -m scrapers.service.silver_cleaning.silver_ingest`. Takes no
# arguments - dbt's project/profiles dirs and Postgres connection come from
# scrapers/dbt/ and the environment (see scrapers/config/dbt.py).
#
# Usage:
#   scrapers/script/run_silver_build.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

if [[ -z "${VIRTUAL_ENV:-}" && -f ".venv/bin/activate" ]]; then
    # shellcheck disable=SC1091
    source ".venv/bin/activate"
fi

exec python3 -m scrapers.service.silver_cleaning.silver_ingest
