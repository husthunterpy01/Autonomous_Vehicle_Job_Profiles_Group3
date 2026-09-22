#!/usr/bin/env bash
# Screens pre-filtered jobs for AV relevance via the LLM (stage 1 of 2; see
# run_enricher.sh for categories/skills). Same as
# `python3 -m scrapers.utils.job_classifier`. Resumable: rerunning the same
# command skips job ids already present in the output files.
#
# Usage:
#   scrapers/script/run_classifier.sh --input data/job_prefilter/llm_candidates.jsonl --output-dir data/job_classification
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

if [[ -z "${VIRTUAL_ENV:-}" && -f ".venv/bin/activate" ]]; then
    # shellcheck disable=SC1091
    source ".venv/bin/activate"
fi

exec python3 -m scrapers.utils.job_classifier "$@"
