#!/usr/bin/env bash
# For each READY_TO_PUBLISH/<package>/manifest.json, if the document file
# is missing locally and "driveFileId" is set in the manifest, fetch the
# file from Google Drive via gdown.
#
# Run this once on the machine that will perform the Issuu uploads,
# before running scripts/upload_all.sh.
#
# Requires: gdown (pip install gdown), jq.

set -uo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
root="$(cd "$here/.." && pwd)"
publish_dir="$root/READY_TO_PUBLISH"

command -v gdown >/dev/null || { echo "gdown not installed. Run: pip install gdown" >&2; exit 1; }
command -v jq    >/dev/null || { echo "jq not installed" >&2; exit 1; }
[[ -d "$publish_dir" ]] || { echo "no $publish_dir directory" >&2; exit 1; }

fetched=()
present=()
failed=()

for d in "$publish_dir"/*/; do
  name=$(basename "$d")
  [[ "$name" == _* ]] && continue
  manifest="$d/manifest.json"
  [[ -f "$manifest" ]] || continue

  file=$(jq -r '.file' "$manifest")
  file_path="$d/$file"
  drive_id=$(jq -r '.driveFileId // ""' "$manifest")

  if [[ -f "$file_path" ]]; then
    echo "$name: $file already present"
    present+=("$name")
    continue
  fi
  if [[ -z "$drive_id" ]]; then
    echo "$name: no driveFileId; nothing to fetch"
    failed+=("$name (no driveFileId)")
    continue
  fi

  echo "$name: fetching $drive_id -> $file"
  if gdown "$drive_id" -O "$file_path"; then
    # gdown can exit 0 while writing an HTML "permission"/quota page instead of
    # the file (e.g. the Drive file isn't shared "Anyone with the link", or the
    # host can't reach drive.google.com). Verify we actually got a PDF.
    if [[ "$(head -c 5 "$file_path" 2>/dev/null)" == "%PDF-" ]]; then
      fetched+=("$name")
    else
      echo "  downloaded content is not a PDF (likely a Drive permission/error page)"
      echo "  -> confirm the file is shared 'Anyone with the link' and reachable"
      rm -f "$file_path"
      failed+=("$name (not a PDF)")
    fi
  else
    echo "  FAILED"
    rm -f "$file_path"
    failed+=("$name (gdown error)")
  fi
done

echo
echo "=== summary ==="
echo "fetched (${#fetched[@]}): ${fetched[*]:-}"
echo "present (${#present[@]}): ${present[*]:-}"
echo "failed  (${#failed[@]}):  ${failed[*]:-}"

[[ ${#failed[@]} -eq 0 ]]
