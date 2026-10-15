#!/usr/bin/env bash
set -euo pipefail
backend="${1:?Pass the exact backend image reference}"
frontend="${2:?Pass the exact frontend image reference}"
reports="${3:-reports/trivy}"
mkdir -p "$reports"
trivy --version > "$reports/trivy-version.txt"
gate=0
for component in backend frontend; do
  image="$backend"
  [[ "$component" != frontend ]] || image="$frontend"
  # Include unfixed findings; no ignore file, ignored CVEs, or soft-fail flag.
  if trivy image --scanners vuln --severity HIGH,CRITICAL --exit-code 1 \
      --ignore-unfixed=false --ignorefile /dev/null --timeout 10m \
      --format json --output "$reports/${component}.json" "$image"; then
    status=0
  else
    status=$?
    gate=1
  fi
  printf '%s\n' "$status" > "$reports/${component}-exit-code.txt"
  printf '%s scan exit code: %s\n' "$component" "$status"
done
if [[ "$gate" -ne 0 ]]; then
  echo 'Release blocked: a vulnerability gate or scanner operation failed.' >&2
  exit 1
fi
echo 'Both strict HIGH/CRITICAL gates passed.'
