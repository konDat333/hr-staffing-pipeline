#!/usr/bin/env sh
# Load the Excel exports into DuckDB, then build and test the dbt project.
# Extra arguments are passed to main.py (e.g. --max-invalid-share 0.5).
set -eu

cd "$(dirname "$0")"

uv run main.py "$@"

cd dbt
uv run dbt build
