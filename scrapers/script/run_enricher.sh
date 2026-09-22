#!/usr/bin/env bash
# Extracts categories and skills for jobs already marked AV-relevant (stage
# 2 of 2; see run_classifier.sh for the relevance screen). Same as
# `python3 -m scrapers.utils.job_enricher`. Resumable like run_classifier.sh.
#
# Usage:
#   scrapers/script/run_enricher.sh                          # defaults to data/job_classification/av_candidates.jsonl
#   scrapers/script/run_enricher.sh --input data/job_classification/av_candidates.jsonl --output-dir data/job_classification
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

if [[ -z "${VIRTUAL_ENV:-}" && -f ".venv/bin/activate" ]]; then
    # shellcheck disable=SC1091
    source ".venv/bin/activate"
fi

exec python3 -m scrapers.utils.job_enricher "$@"
