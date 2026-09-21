#!/usr/bin/env bash
# Runs the scraper the same way `python3 -m scrapers.scraper_main` does, but
# without having to remember the module path, the repo-root working
# directory it requires (YAML paths and load_dotenv() are relative to cwd -
# see scrapers/config/dbt.py and the root README's Scrapers section), or to
# activate the venv by hand.
#
# Usage:
#   scrapers/script/run_scraper.sh                              # every enabled API company
#   scrapers/script/run_scraper.sh --company stack_av --max-jobs 10
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

if [[ -z "${VIRTUAL_ENV:-}" && -f ".venv/bin/activate" ]]; then
    # shellcheck disable=SC1091
    source ".venv/bin/activate"
fi

exec python3 -m scrapers.scraper_main "$@"
