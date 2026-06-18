#!/usr/bin/env bash
# Drive every READY_TO_PUBLISH/<package>/issuu_command.sh, with a summary at the end.
# Failures in one package do not abort the loop.
#
# Usage: upload_all.sh
# Optional: DRY_RUN=1 to dry-run all packages.

set -uo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
root="$(cd "$here/.." && pwd)"
publish_dir="$root/READY_TO_PUBLISH"

[[ -d "$publish_dir" ]] || { echo "no $publish_dir directory" >&2; exit 1; }

ok=()
failed=()
skipped=()

for d in "$publish_dir"/*/; do
  [[ -d "$d" ]] || continue
  name=$(basename "$d")
  [[ "$name" == _* ]] && continue   # skip _template etc.
  echo "=== $name ==="
  if [[ ! -f "$d/issuu_command.sh" ]]; then
    echo "  (no issuu_command.sh — skipping)"
    skipped+=("$name")
    continue
  fi
  if bash "$d/issuu_command.sh"; then
    ok+=("$name")
  else
    rc=$?
    echo "  FAILED (exit $rc)"
    failed+=("$name")
  fi
done

echo
echo "=== summary ==="
echo "ok      (${#ok[@]}):      ${ok[*]:-}"
echo "failed  (${#failed[@]}):  ${failed[*]:-}"
echo "skipped (${#skipped[@]}): ${skipped[*]:-}"

[[ ${#failed[@]} -eq 0 ]]
