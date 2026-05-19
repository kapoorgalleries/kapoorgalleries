#!/usr/bin/env bash
# Upload a single package to Issuu via the v2 API.
# Usage: issuu_upload.sh <package-dir>
# Reads <package-dir>/manifest.json for metadata, uploads <package-dir>/<file>,
# and writes a .uploaded marker on success so reruns are idempotent.
#
# Required: ISSUU_API_TOKEN env var, curl, jq.
# Optional: DRY_RUN=1 to print actions without hitting the API.

set -euo pipefail

ISSUU_API="${ISSUU_API:-https://api.issuu.com/v2}"
DRY_RUN="${DRY_RUN:-0}"

die() { echo "ERROR: $*" >&2; exit 1; }
log() { echo "[$(date +%H:%M:%S)] $*"; }

[[ $# -eq 1 ]] || die "usage: $0 <package-dir>"
pkg_dir="$1"
[[ -d "$pkg_dir" ]] || die "not a directory: $pkg_dir"

manifest="$pkg_dir/manifest.json"
marker="$pkg_dir/.uploaded"
[[ -f "$manifest" ]] || die "missing manifest: $manifest"

if [[ -f "$marker" ]]; then
  log "already uploaded ($marker), skipping. Delete the marker to force reupload."
  exit 0
fi

command -v jq   >/dev/null || die "jq is required but not installed"
command -v curl >/dev/null || die "curl is required but not installed"
[[ -n "${ISSUU_API_TOKEN:-}" ]] || die "ISSUU_API_TOKEN is not set"

file=$(jq -r '.file'                            "$manifest")
title=$(jq -r '.title'                          "$manifest")
desc=$(jq -r  '.description // ""'              "$manifest")
access=$(jq -r '.access // "PUBLIC"'            "$manifest")
publish=$(jq -r '.publish // false'             "$manifest")
orig_date=$(jq -r '.originalPublishDate // ""'  "$manifest")
downloadable=$(jq -r '.downloadable // false'   "$manifest")
preview=$(jq -r '.preview // false'             "$manifest")
pub_type=$(jq -r '.type // "editorial"'         "$manifest")

[[ -n "$title"  && "$title"  != "null" ]] || die "manifest missing 'title'"
[[ -n "$file"   && "$file"   != "null" ]] || die "manifest missing 'file'"
file_path="$pkg_dir/$file"
[[ -f "$file_path" ]] || die "file not found: $file_path"

log "package : $(basename "$pkg_dir")"
log "file    : $file ($(du -h "$file_path" | cut -f1))"
log "title   : $title"
log "access  : $access"
log "publish : $publish"

if [[ "$DRY_RUN" == "1" ]]; then
  log "DRY_RUN=1 — skipping API calls"
  exit 0
fi

# Per Issuu v2 docs: when uploading the file via a separate PATCH (rather than
# providing fileUrl up front), the draft creation body omits confirmCopyright
# and fileUrl. confirmCopyright is sent with the upload PATCH instead.
draft_body=$(jq -n \
  --arg title "$title" \
  --arg desc "$desc" \
  --arg access "$access" \
  --arg pub_type "$pub_type" \
  --arg orig_date "$orig_date" \
  --argjson downloadable "$downloadable" \
  --argjson preview "$preview" \
  '{
    info: ({
      title: $title,
      description: $desc,
      access: $access,
      type: $pub_type,
      showDetectedLinks: true,
      downloadable: $downloadable,
      preview: $preview
    } + (if $orig_date != "" then {originalPublishDate: $orig_date} else {} end))
  }')

log "creating draft..."
draft_resp=$(curl -sS --fail-with-body -X POST "$ISSUU_API/drafts" \
  -H "Authorization: Bearer $ISSUU_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d "$draft_body") || die "draft creation failed: $draft_resp"

slug=$(echo "$draft_resp" | jq -r '.slug // empty')
[[ -n "$slug" ]] || die "no slug in draft response: $draft_resp"
log "draft slug: $slug"

log "uploading file..."
upload_resp=$(curl -sS --fail-with-body -X PATCH "$ISSUU_API/drafts/$slug/upload" \
  -H "Authorization: Bearer $ISSUU_API_TOKEN" \
  -F "confirmCopyright=true" \
  -F "file=@$file_path") || die "file upload failed: $upload_resp"
log "upload accepted"

public_url=""
if [[ "$publish" == "true" ]]; then
  log "publishing..."
  publish_resp=$(curl -sS --fail-with-body -X POST "$ISSUU_API/drafts/$slug/publish" \
    -H "Authorization: Bearer $ISSUU_API_TOKEN") || die "publish failed: $publish_resp"
  public_url=$(echo "$publish_resp" | jq -r '.publicLocation // .location // empty')
  log "published${public_url:+: $public_url}"
else
  log "left as draft (set \"publish\": true in manifest to publish)"
fi

{
  echo "uploaded_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "slug=$slug"
  echo "publish=$publish"
  [[ -n "$public_url" ]] && echo "url=$public_url"
} > "$marker"

log "done"
