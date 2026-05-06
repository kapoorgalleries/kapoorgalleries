"""Fetch every source listed in ``catalog/sources.yaml`` from Drive.

For each entry that has a ``drive_file_id`` and a ``local_path``, download the
file with ``gdown``. Skips entries marked ``enabled: false`` and entries
whose local file already exists (use ``--force`` to re-fetch).

Run from the repo root:
    python scripts/fetch_drive.py             # one-shot
    python scripts/fetch_drive.py --force     # re-download everything
    python scripts/fetch_drive.py --only artsy_csv  # one type
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

try:
    import gdown
except ImportError:
    print("gdown not installed.  pip install gdown", file=sys.stderr)
    sys.exit(1)

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "catalog" / "sources.yaml"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="re-download files that already exist")
    ap.add_argument("--only", default=None, help="only fetch sources of this type")
    args = ap.parse_args()

    entries = yaml.safe_load(SOURCES.read_text()) or []
    n_fetched = 0
    n_skipped = 0
    n_disabled = 0
    n_no_id = 0

    for entry in entries:
        name = entry.get("name", "?")
        if not entry.get("enabled", True):
            n_disabled += 1
            continue
        if args.only and entry.get("type") != args.only:
            continue
        drive_id = entry.get("drive_file_id", "")
        local = entry.get("local_path")
        if not drive_id or drive_id.startswith("gmail:") or not local:
            n_no_id += 1
            continue

        local_path = ROOT / local
        local_path.parent.mkdir(parents=True, exist_ok=True)

        if local_path.exists() and not args.force:
            print(f"  ✓ {name} (already at {local})")
            n_skipped += 1
            continue

        url = f"https://drive.google.com/uc?id={drive_id}"
        print(f"  ↓ {name}")
        try:
            gdown.download(url, str(local_path), quiet=False, fuzzy=True)
            n_fetched += 1
        except Exception as e:
            print(f"    failed: {e}")

    print()
    print(f"Fetched: {n_fetched}  |  Already cached: {n_skipped}  |  "
          f"Disabled: {n_disabled}  |  No drive_file_id: {n_no_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
