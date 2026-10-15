#!/usr/bin/env bash
set -euo pipefail
# Official Linux amd64 release; checksum verified against the publisher's file.
version=0.76.0
checksum=e24b1c51293c1b15e4ba8d45bbc7891ba053f90278ec2698f3562c993e145fe7
destination="${1:?Pass the installation directory}"
mkdir -p "$destination"
download="$(mktemp -d)"
trap 'rm -rf -- "$download"' EXIT
curl --fail --silent --show-error --location --retry 3 \
  "https://github.com/aquasecurity/trivy/releases/download/v${version}/trivy_${version}_Linux-64bit.tar.gz" \
  --output "$download/trivy.tar.gz"
printf '%s  %s\n' "$checksum" "$download/trivy.tar.gz" | sha256sum --check --strict
tar -xzf "$download/trivy.tar.gz" -C "$destination" trivy
"$destination/trivy" --version
