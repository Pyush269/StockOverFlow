# Prompt 4: CI, security gates, and GHCR releases

Repository: [Pyush269/StockOverFlow](https://github.com/Pyush269/StockOverFlow). Workflow: [StockFlow CI](https://github.com/Pyush269/StockOverFlow/actions/workflows/ci.yml). Implemented on 15 October 2026.

## Workflow and trust boundaries

The active YAML is `.github/workflows/ci.yml`; every external action is pinned to an immutable verified commit, annotated with its release version. Dependabot checks action pins and application Docker bases weekly. The runner is GitHub-hosted Ubuntu 24.04, with Python 3.12 and Node 22.23.2.

1. **tests:** start an isolated PostgreSQL 16 service using public test-only credentials and database `stockflow_test`; install the locked Python dependencies; migrate the empty database and check schema parity; run all 49 backend tests, including migration round trip, locking and rollback. Run `npm ci`, 11 frontend unit tests, and the production build. Save JUnit and frontend output.
2. **images:** after tests succeed, build/load each release image once for Linux/amd64, tagged with the full source SHA and labeled with its repository/revision. Install pinned Trivy 0.76.0 from the official release after validating the hardcoded SHA-256 checksum. Scan both exact images; save both JSON reports even when a scan fails.
3. **publish:** only after both jobs succeed, and only for a `push` to `refs/heads/main`, download this run's image archive. Verify its SHA-256 and loaded image IDs against build-job outputs. Log in with the automatic `GITHUB_TOKEN`, tag and push the loaded images without rebuilding, record registry digests, and log out. Transient registry upload errors get three bounded attempts using the same image bytes; the job fails if all fail.

Pull requests receive `contents: read`, no registry login, no package write token, and no persisted checkout credentials. The workflow never uses `pull_request_target`. Manual dispatch runs validation but skips publishing. The write-enabled publish job does not check out source, execute repository scripts, run downloaded containers, or rebuild images. The image archive is produced only after both gates pass; failed tests also block the image job through `needs`.

Artifact names include the source SHA. Test reports remain for 14 days, scan/publication reports for 30 days, and the large image-transfer archive for 3 days. Overwriting same-name artifacts supports reruns of the same source commit; the workflow attempt logs retain execution details. PR runs may validate images but cannot publish them.

## Strict security policy and remediation

The scanner command includes:

```bash
trivy image --scanners vuln --severity HIGH,CRITICAL --exit-code 1 \
  --ignore-unfixed=false --ignorefile /dev/null --timeout 10m \
  --format json --output reports/trivy/backend.json <exact-image>
```

The frontend receives the same policy. A vulnerability finding, scanner failure, or unavailable database fails validation. There is no `continue-on-error`, `--ignore-unfixed`, CVE exception list, or weakening of the gate. Both images are attempted so reports remain useful even if the first fails.

The initial Debian 12 backend image reported **55 package findings: 53 HIGH and 2 CRITICAL, covering 15 distinct CVEs**. Several had no vendor fix. The backend base was changed to the official, digest-pinned Python 3.12 Alpine image. The same pinned application dependency set installs with musl wheels; the runtime remains non-root and read-only under Compose. Both final application images pass the selected gate with **zero HIGH/CRITICAL findings at scan time**. This is not a claim of permanent vulnerability freedom; each CI run refreshes the vulnerability database.

After the base change, all 49 tests passed against PostgreSQL on Alpine Linux. All 8 real Chromium workflows, Nginx recovery, business rules, migration parity, and persistence after Compose down/up passed again. The separate tests build target is not included in the final runtime stage. The existing upstream TestClient warning remains non-blocking.

Local execution of the actual build/scan/package scripts also verified the archive checksum and unchanged image IDs after reload. A reconstructed prior Debian image was fed to the same scanner script: the backend report contained real HIGH/CRITICAL findings, returned exit 1, and the clean frontend was still scanned with exit 0. This proves rejection based on vulnerabilities rather than a scanner infrastructure failure.

## Evidence and release identification

The [successful release run](https://github.com/Pyush269/StockOverFlow/actions/runs/38720078293), report links, source SHA, and registry digests are captured in [CI_RELEASE.json](CI_RELEASE.json). Saved scan reports are under [security/](security/). The workflow summary records both the source SHA and published repository digests. Image IDs identify scanned filesystem/config content; registry manifest digests identify pulled release references. They are different identifiers.

```text
ghcr.io/pyush269/stockflow-backend:<full-source-sha>
ghcr.io/pyush269/stockflow-frontend:<full-source-sha>
```

No mutable `latest` release is published. Later deployment values should pin a verified source SHA or immutable registry digest. Changes to documentation also run the full pipeline; the evidence file records a concrete completed run, not a promise that future runs pass.

## Package access before EKS

Both recorded SHA-tagged images were successfully inspected from a fresh Docker CLI container with no registry credentials, confirming anonymous registry access. No package-visibility step remains for that release. Public repository visibility alone should never be treated as proof of package access. If a future package is private, use **Package settings → Change visibility → Public** for anonymous instructor/EKS pulls:

- [Backend package](https://github.com/users/Pyush269/packages/container/package/stockflow-backend)
- [Frontend package](https://github.com/users/Pyush269/packages/container/package/stockflow-frontend)

Afterward verify `docker pull ghcr.io/pyush269/stockflow-backend:<sha>` and the matching frontend image without registry credentials. If packages remain private, the later Helm stage must configure an appropriate image-pull Secret for both Deployments and the migration Job. Public source visibility and a passing publisher login do not verify anonymous pull access. The CI publisher needs no personal token; private cluster pulls are a separate credential decision.

## Reproduce locally

On this Windows computer, use Docker Desktop's Linux engine:

```powershell
docker compose -f compose.ci.yml up --build --abort-on-container-exit --exit-code-from backend-tests
docker compose -f compose.ci.yml down
& .\scripts\test-containers.ps1
```

The CI Compose project has no host ports or development data volume. The main development database is never targeted. With the installed Trivy on PATH, scan the local images directly:

```powershell
trivy image --scanners vuln --severity HIGH,CRITICAL --exit-code 1 stockflow-backend:local
trivy image --scanners vuln --severity HIGH,CRITICAL --exit-code 1 stockflow-frontend:local
```

The reusable `scripts/ci/*.sh` scripts run under Bash/Linux in GitHub Actions. GitHub's test JUnit/frontend outputs, Trivy JSON reports, verified-image manifest, and publication receipts are available in each run's artifacts. Re-running validation does not deploy anything to AWS.

Next: **Prompt 5**, reviewable Terraform/EKS configuration and plan. No AWS infrastructure has been provisioned by this phase.

References: [GitHub package publishing](https://docs.github.com/en/packages/managing-github-packages-using-github-actions-workflows/publishing-and-installing-a-package-with-github-actions), [Trivy image CLI](https://trivy.dev/docs/v0.76/reference/configuration/cli/trivy_image/), [package visibility](https://docs.github.com/en/packages/learn-github-packages/configuring-a-packages-access-control-and-visibility).
