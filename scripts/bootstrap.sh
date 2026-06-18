#!/usr/bin/env bash
#
# One-time local bootstrap: install deps, fetch every Drive file listed in
# catalog/sources.yaml into data/raw/, then run the full pipeline.
#
# Usage:
#   ./scripts/bootstrap.sh                   # fetch + build everything
#   SKIP_FETCH=1 ./scripts/bootstrap.sh      # just rebuild from existing raw/
#
# Auth:
#   gdown handles public-share links automatically.  For private files (most
#   of the Kapoor Drive), gdown will fall back to the system browser and ask
#   you to log in once.  The fetched files land in data/raw/ which is
#   gitignored, so re-running the script is safe.
set -euo pipefail

cd "$(dirname "$0")/.."

if ! python3 -c "import gdown" 2>/dev/null; then
  echo "Installing gdown…"
  pip install --quiet gdown
fi

if ! python3 -c "import pdfplumber" 2>/dev/null; then
  echo "Installing project deps…"
  pip install --quiet -e '.[dev]'
fi

if [[ -z "${SKIP_FETCH:-}" ]]; then
  echo "Fetching sources from Drive into data/raw/…"
  python3 scripts/fetch_drive.py
fi

echo
echo "Running pipeline…"
make all

echo
echo "Done. Open data/master.csv, reports/coverage_report.md, and inspect."
