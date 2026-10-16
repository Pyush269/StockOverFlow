# Pipeline narration guide

The MP4 is deliberately silent. Read these suggestions in your own voice and
adjust the pacing while editing. Shorten waiting time if helpful, while keeping
the start, progress, and final result of the actual run visible.

## Suggested narration

**Introduction:** This video shows StockFlow's working continuous integration
pipeline, from a real push to GitHub through publication of scanned images.

**Tests:** The first job upgrades an empty PostgreSQL database, checks migration
parity, runs 49 backend tests, and runs the frontend unit tests and build.

**Build and security gates:** The next job builds both application images once.
Trivy scans operating-system packages and application dependencies. Any HIGH or
CRITICAL vulnerability blocks publication, including unfixed findings. This image
gate is separate from the documented Terraform configuration findings.

**Publication design:** Publication depends on both earlier jobs. It downloads
the exact scanned images, verifies their checksum and identities, and publishes
both images to GHCR using the full source commit SHA. It does not rebuild them.

**Push and live run:** This is the actual git push output. The source commit
matches the GitHub Actions run shown next. The diagram shows the dependency
between testing, image scanning, and publication. The recording keeps the real
waiting and progression visible; no result is simulated.

**Test result:** All 49 backend tests passed. All 11 frontend unit tests passed,
and the production frontend build completed. The tests use a disposable test
database rather than the deployed inventory database.

**Scan result:** Both image scans returned exit code zero, and the strict gate
passed. The scan reports and verified image archive are retained as artifacts.

**Publication result:** The archive checksum and loaded image identities were
verified before upload. The final receipts show the backend and frontend image
digests. Both tags use the same source SHA as this successful run.

**Conclusion:** All three pipeline jobs succeeded. Publishing an image does not
automatically change the live application's release values; the separate GitOps
promotion controls which published images ArgoCD deploys.

## Actual chapter times

- **00:00** — Introduction
- **00:08** — Tests are the first gate
- **00:19** — Build once, then scan
- **00:30** — Publish the scanned image bytes
- **00:50** — Actual git push
- **01:02** — Live GitHub Actions run
- **01:04** — Pipeline progress
- **02:06** — Pipeline progress
- **04:32** — Pipeline progress
- **04:37** — Final GitHub result
- **05:00** — PostgreSQL tests and frontend build
- **05:18** — Build once and scan release images
- **05:36** — Publish scanned images to GHCR
- **05:54** — Pipeline complete

Actual run: https://github.com/Pyush269/StockOverFlow/actions/runs/38867618119

Recorded source commit: `e207e786c6df07b2f270b1d5120a5fc78b8edfc1`.

This video covers the CI/CD chapter. The full capstone presentation also needs the slides, application/code, AWS Console, ArgoCD, Kubernetes, Prometheus, and Grafana.
