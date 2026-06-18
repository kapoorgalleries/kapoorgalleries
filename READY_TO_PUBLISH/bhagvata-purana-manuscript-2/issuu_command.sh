#!/usr/bin/env bash
# Per-package wrapper: hands off to the shared uploader with this directory as the package root.
# Copy this file (and manifest.json) into each READY_TO_PUBLISH/<package>/ directory.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
root="$(cd "$here/../.." && pwd)"
exec "$root/scripts/issuu_upload.sh" "$here"
