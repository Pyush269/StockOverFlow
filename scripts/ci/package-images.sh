#!/usr/bin/env bash
set -euo pipefail
: "${SOURCE_SHA:?Set the source commit SHA}"
: "${GITHUB_OUTPUT:?Set the job output file}"
destination="${1:-release}"
mkdir -p "$destination"
backend="stockflow-backend:$SOURCE_SHA"
frontend="stockflow-frontend:$SOURCE_SHA"
backend_id="$(docker image inspect --format '{{.Id}}' "$backend")"
frontend_id="$(docker image inspect --format '{{.Id}}' "$frontend")"
docker save --output "$destination/images.tar" "$backend" "$frontend"
archive_sha256="$(sha256sum "$destination/images.tar" | cut -d ' ' -f 1)"
printf 'source_sha=%s\nbackend_id=%s\nfrontend_id=%s\narchive_sha256=%s\n' \
  "$SOURCE_SHA" "$backend_id" "$frontend_id" "$archive_sha256" > "$destination/manifest.txt"
printf 'backend_id=%s\nfrontend_id=%s\narchive_sha256=%s\n' \
  "$backend_id" "$frontend_id" "$archive_sha256" >> "$GITHUB_OUTPUT"
if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
  {
    printf '### Scanned release images\n\nSource commit: `%s`\n\n' "$SOURCE_SHA"
    printf '| Image | Scanned image ID |\n|---|---|\n'
    printf '| Backend | `%s` |\n| Frontend | `%s` |\n' "$backend_id" "$frontend_id"
    printf '\nArchive SHA-256: `%s`\n' "$archive_sha256"
  } >> "$GITHUB_STEP_SUMMARY"
fi
