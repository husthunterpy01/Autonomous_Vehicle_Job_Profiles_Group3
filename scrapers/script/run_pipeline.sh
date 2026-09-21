#!/usr/bin/env bash
# Runs the whole pipeline end to end: scrape -> MinIO -> bronze -> Silver
# (dbt) -> export -> AV pre-filter -> LLM relevance -> LLM category/skill
# enrichment. Same as `python3 -m scrapers.pipeline_main`, just without
# having to cd to the repo root or activate the venv by hand.
#
# Usage:
#   scrapers/script/run_pipeline.sh                          # full chain, every enabled company
#   scrapers/script/run_pipeline.sh --company stack_av
#   scrapers/script/run_pipeline.sh --skip-scrape             # start from existing bronze data
#   scrapers/script/run_pipeline.sh --skip-scrape --skip-silver-build   # rerun just the LLM stages
#
# For a single stage on its own (e.g. just re-export Silver, or just rerun
# enrichment), use that stage's own run_*.sh script instead.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

if [[ -z "${VIRTUAL_ENV:-}" && -f ".venv/bin/activate" ]]; then
    # shellcheck disable=SC1091
    source ".venv/bin/activate"
fi

exec python3 -m scrapers.pipeline_main "$@"
