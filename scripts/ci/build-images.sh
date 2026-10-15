#!/usr/bin/env bash
set -euo pipefail
: "${SOURCE_SHA:?Set the full source commit SHA}"
: "${SOURCE_URL:?Set the source repository URL}"
[[ "$SOURCE_SHA" =~ ^[0-9a-f]{40}$ ]] || { echo 'Expected a full Git SHA' >&2; exit 1; }
for component in backend frontend; do
  # One release build per component; later steps scan/save this loaded image.
  docker buildx build --load --platform linux/amd64 --provenance=false \
    --label "org.opencontainers.image.source=$SOURCE_URL" \
    --label "org.opencontainers.image.revision=$SOURCE_SHA" \
    --tag "stockflow-${component}:${SOURCE_SHA}" "$component"
done
