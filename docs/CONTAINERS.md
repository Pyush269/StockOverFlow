# Prompt 3: container operation and verification

Verified on 15 October 2026 with Docker Desktop's Linux/amd64 engine and Compose v5.6.0. `docker compose up --build` now starts the complete application; append `-d --wait` to run in the background and wait for health checks.

## Services and startup

| Service | Runtime | Startup condition | Host access |
|---|---|---|---|
| postgres | PostgreSQL 16 Alpine, named volume | PostgreSQL health check | 127.0.0.1:5432 |
| migrate | Backend image; Alembic upgrade | PostgreSQL healthy | None; exits 0 |
| backend | Python 3.12 slim, UID/GID 10001 | PostgreSQL healthy; migration succeeded | 127.0.0.1:8000 |
| frontend | React / unprivileged Nginx, UID/GID 101 | Backend `/ready` healthy | 127.0.0.1:3000 -> 8080 |

The backend installs the runtime lock into a virtual environment in a build stage, then copies the environment, API, and Alembic files to the runtime. The frontend uses Node 22 and `npm ci` to build, then copies only the bundle into Nginx; Node/npm/Playwright are absent from that runtime. All base images, including PostgreSQL, are digest-pinned. Maintain these pins; reproducibility does not establish vulnerability status.

Application/migration containers use read-only root filesystems, dropped capabilities, `no-new-privileges`, an init process, and writable temporary `/tmp`. Nginx config/PID/temp files live in `/tmp`. Dockerignore allowlists exclude host dependencies, virtual environments, tests, logs, and secrets from build contexts. The ignored `.env` is not copied into images.

## Routing and settings

The browser calls relative `/api/...` URLs. Nginx preserves the API path, status, JSON error body, and empty DELETE response. SPA paths fall back to `index.html`; missing assets return 404. Hashed assets are cached; index HTML revalidates.

`API_UPSTREAM` defaults to `backend:8000`. `NGINX_RESOLVER` defaults to Docker's DNS `127.0.0.11`. Both are substituted at startup after input validation; Nginx variables such as `$uri` remain intact. Nginx re-resolves its upstream so backend replacement does not require restarting the frontend. These settings are runtime configuration, not JavaScript build values.

Kubernetes will require the actual backend Service hostname and cluster DNS address if retaining this proxy. The planned ALB routes `/api` directly to the backend Service. The future Helm configuration must handle that environment rather than assume Docker DNS exists there.

Compose constructs its own `DATABASE_URL` from `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD`, with host `postgres`. The `.env` URL using localhost is for host development. Choose an alphanumeric local password to avoid URI escaping issues. `POSTGRES_PORT`, `BACKEND_PORT`, and `FRONTEND_PORT` optionally change host ports. The application remains unauthenticated and loopback-bound.

## Local operation

From `stockflow/` with Docker Desktop running and the existing ignored `.env` intact:

```powershell
docker compose config --quiet
docker compose up --build -d --wait
docker compose ps --all
docker compose logs migrate backend frontend
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/ready
```

Open [StockFlow](http://127.0.0.1:3000), [Swagger](http://127.0.0.1:8000/docs), or [metrics](http://127.0.0.1:8000/metrics). Migration **Exited (0)** means success; all other services should be healthy. Frontend `/health` checks static serving; backend `/ready` checks database/schema readiness.

```powershell
docker compose down
docker compose up -d --wait
```

Normal `down` preserves `stockflow_postgres-data`. **`down --volumes` deletes inventory.** A different Compose project name normally creates another volume. Changing `.env` passwords does not update an initialized PostgreSQL role; preserve credentials or rotate them deliberately.

The host API and container API both use port 8000. Stop the host API before starting the stack. To switch back, run `docker compose stop frontend backend`, then use the host development helpers. Vite on 5173 may also run against the container API for frontend-only edits.

## Repeatable verification

From `stockflow/`, with Node 22 and frontend development dependencies installed:

```powershell
& .\scripts\test-containers.ps1
# API/container checks only, if Chromium is not installed:
& .\scripts\test-containers.ps1 -SkipBrowser
```

For first-time browser setup, run from `frontend/`:

```powershell
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path (Split-Path $PWD.Path -Parent) '.playwright-browsers'
node node_modules/playwright/cli.js install chromium --no-shell
```

The helper uses the explicit disposable project `stockflow-container-qa`, an independent named volume, public test-only credentials, and ports 3001/8002/5434. It refuses occupied QA ports or an existing QA volume, and clears/restores conflicting process settings. Final cleanup removes only this QA project's disposable volume. The backend host virtual environment is not needed, and the development inventory is never targeted.

Recorded checks passed:

- Both images build on Linux using locked dependencies; backend `pip check` succeeds.
- Empty-database migration succeeds before API startup; three long-running services become healthy.
- Actual runtime non-root UIDs, read-only root filesystems, and generated Nginx configuration.
- Alembic reports no schema/model drift.
- Nginx-proxied CRUD, duplicate SKU, validation, search, protected deletion, and error envelopes.
- Receive 10, issue 3, reject 8: quantity remains 7 with exactly two ledger entries.
- SPA fallback, missing-asset 404, and API JSON errors preserved through Nginx.
- Backend replacement recovers through the unchanged frontend container.
- All **8 Chromium browser workflows** against the production bundle, including mobile, concurrency conflicts, and failed-save recovery.
- Full Compose `down` / `up`, including recreating PostgreSQL, preserves exact product fields, quantity 7, and both ledger entries.

Evidence: [terminal output](CONTAINER_TEST_RESULTS.txt), [running main-stack checks](CONTAINER_LIVE_RESULTS.json), [desktop](screenshots/container-overview-qa.png), and [mobile](screenshots/container-mobile-qa.png). Screenshots contain isolated QA fixtures. A before/after comparison confirms the main project's original product and 7 units were preserved when switching to containers; frontend, proxied API, Swagger, health, readiness, and metrics return 200.

## Troubleshooting

- **Port allocated:** identify the existing listener and stop the matching development server, or select another host port.
- **Migration fails:** inspect `docker compose logs migrate`. Correct the cause and rerun Compose. The backend remains blocked; API startup never creates or migrates tables.
- **Readiness 503:** inspect backend/PostgreSQL logs and migration revision. Liveness alone does not establish database readiness.
- **Authentication failure:** verify `.env` matches credentials initialized in the named volume. Do not delete inventory as a routine password fix.
- **Proxy 502:** verify backend health and both Nginx settings, then inspect frontend logs. Allow a few seconds for DNS refresh after backend replacement. Rerun Compose after configuration changes.
- **Engine unavailable:** start Docker Desktop and wait for its Linux engine.

## Limits and next stage

This verifies local Linux/amd64, not multi-platform images, Kubernetes, cloud deployment, or production security. Earlier phase reports record 49 backend tests and 11 frontend unit tests; this helper runs 8 browser workflows and focused container checks. Safari/Firefox and a full accessibility audit remain unverified.

Next is **Prompt 4**: GitHub Actions, Linux PostgreSQL integration checks, strict Trivy HIGH/CRITICAL gates, and publication of the exact scanned images to GHCR. This phase does not claim a passing vulnerability scan or registry publication.

References: [Compose startup ordering](https://docs.docker.com/compose/how-tos/startup-order/), [unprivileged Nginx image](https://github.com/nginx/docker-nginx-unprivileged), [Nginx upstream resolution](https://nginx.org/en/docs/http/ngx_http_upstream_module.html#resolve).
