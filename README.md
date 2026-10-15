# StockFlow

[![StockFlow CI](https://github.com/Pyush269/StockOverFlow/actions/workflows/ci.yml/badge.svg)](https://github.com/Pyush269/StockOverFlow/actions/workflows/ci.yml)
[![Terraform validation](https://github.com/Pyush269/StockOverFlow/actions/workflows/terraform.yml/badge.svg)](https://github.com/Pyush269/StockOverFlow/actions/workflows/terraform.yml)
[![Helm validation](https://github.com/Pyush269/StockOverFlow/actions/workflows/helm.yml/badge.svg)](https://github.com/Pyush269/StockOverFlow/actions/workflows/helm.yml)

Source repository: [Pyush269/StockOverFlow](https://github.com/Pyush269/StockOverFlow).

Inventory management with a product catalog, stock receipts/issues, an append-only API ledger, and low-stock reporting. Built for the DevSecOps capstone using React/FastAPI/PostgreSQL and the planned EKS/Helm/ArgoCD delivery architecture.

Stack: Python 3.12, FastAPI, SQLAlchemy/Alembic, PostgreSQL 16, React 19, Vite 8, Nginx, Docker Compose, GitHub Actions/GHCR, Trivy, Terraform, Kubernetes/EKS, Helm, ArgoCD, Prometheus, and Grafana.

## Current stage

**Application/CI and the local Helm, GitOps, and monitoring demonstrations are implemented. AWS stays off at the user's request.** The revised one-worker Sydney plan has **59 additions, no changes or destroys**, estimated at **$0.29/hour for infrastructure**, or **$0.33/hour for the full demo**, before variable usage and credits. Review [costs and three configuration scan findings](docs/INFRASTRUCTURE.md). Local checks cover Helm upgrade/PVC recovery, ArgoCD release/rollback, retained inventory, backend Pod recovery, live Grafana panels, and HPA scaling from two to three replicas and back. Real EKS/ALB/EBS checks and the mandatory cloud walkthrough video remain pending. Use the [deployment/evaluation checklist](docs/DEPLOYMENT_CHECKLIST.md).

- Product CRUD with normalized unique SKUs, search/category filters, and pagination.
- Transactional stock-in/stock-out with PostgreSQL row locks.
- Insufficient-stock and integer-overflow protection.
- Read-only stock history; products with history cannot be deleted.
- Dashboard totals, exact decimal inventory value, low-stock results, and recent movements.
- Alembic migrations, health/schema readiness, Prometheus HTTP metrics, explicit development CORS origins.
- PostgreSQL integration tests, including deterministic lock contention, rollback after a failed ledger write, migration round-trip, and database constraints.
- Responsive React dashboard, searchable/paginated catalog, category/stock filters, create/edit/delete dialogs, receive/issue dialogs, and product history.
- Inline error handling, pending states, success notifications, protected deletion, stale-stock recovery, keyboard-accessible dialogs/navigation, and mobile catalog cards.
- Self-hosted fonts/assets and a development proxy to the real API; no placeholder inventory data.

## Architecture

```text
Current: React/Nginx container -> /api proxy -> FastAPI container -> PostgreSQL 16
Dev:     React/Vite -> /api proxy -> FastAPI -> development PostgreSQL
CI:      GitHub Actions -> tests/build -> strict Trivy gates -> SHA-tagged GHCR images
Local:   Git release values -> ArgoCD/Helm -> isolated Kubernetes demo
Pending: Same GitOps deployment -> AWS EKS -> public ALB
```

The backend never creates tables on startup. Apply Alembic migrations before starting it. Stock changes and ledger inserts share a single transaction. All movement, metadata update, and product delete operations acquire the same product row lock, preventing competing issues from overselling. The database also enforces nonnegative inventory and restricts deletion of referenced products.

## Run the complete application

Docker Desktop must be running with Linux containers. From `stockflow/`, the existing ignored `.env` is already configured on this computer. For a fresh checkout, copy `.env.example` to `.env` and choose a long alphanumeric password; update both password occurrences for host development. Preserve existing database credentials when reusing a volume.

```powershell
docker compose config --quiet
docker compose up --build -d --wait
```

Open [StockFlow](http://127.0.0.1:3000) and [Swagger UI](http://127.0.0.1:8000/docs). The frontend is the production bundle served by non-root Nginx on container port 8080. Host ports 3000, 8000, and 5432 bind only to loopback. Stop a host development API using port 8000 before starting the container API; these are alternative modes.

```powershell
docker compose ps --all
docker compose logs migrate backend frontend
Invoke-RestMethod http://127.0.0.1:8000/ready
docker compose down
# Starts the same database with inventory and ledger preserved:
docker compose up -d --wait
```

The migration container should show **Exited (0)**; it is a successful one-shot job. The other three services should be healthy. `down` preserves `stockflow_postgres-data`; **`down --volumes` deletes inventory**. Application containers use non-root users, read-only root filesystems, dropped Linux capabilities, and temporary writable `/tmp` storage. No Python or Node installation is needed to run the Compose application. See [container operation and verification](docs/CONTAINERS.md).

## Host development on this computer

Prerequisites: Python 3.12, Docker Desktop with Linux containers, and Docker Compose. Tool installation details live in the parent Capstone folder.

From PowerShell in `Capstone\stockflow`:

```powershell
# Use the existing Capstone launcher to expose Docker and Python if needed.
. ..\Enter-Project.ps1

# Already prepared during initial implementation. For a fresh checkout:
python -m venv backend/.venv
& .\backend\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.lock.txt
```

StockFlow has its own environment at `backend/.venv`; it does not use the reference application's installed dependencies. `requirements.txt` pins direct runtime dependencies; `requirements.lock.txt` locks the runtime dependency set. The corresponding development files include pytest/TestClient dependencies. The runtime lock has also been installed and checked successfully on Linux/Python 3.12 in the backend image.

For a fresh checkout, copy `.env.example` to `.env` and replace the password in **both** `POSTGRES_PASSWORD` and `DATABASE_URL`. Use the same value. This checkout already has an ignored `.env` with a generated local password. URL-encode special password characters when constructing database URLs; a long alphanumeric value avoids that issue.

```powershell
# From stockflow/; Docker Desktop must be running.
# If switching from the full stack, stop these before using host port 8000:
docker compose stop frontend backend
docker compose up -d --wait postgres
Set-Location backend
& .\.venv\Scripts\python.exe -m alembic upgrade head
& .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Or, from `stockflow/`, run `& .\scripts\start-backend.ps1` to start the DB, migrate, and run the API in the foreground.

Open [Swagger UI](http://localhost:8000/docs), [health](http://localhost:8000/health), [readiness](http://localhost:8000/ready), and [metrics](http://localhost:8000/metrics). The API is bound to loopback for local development. It currently has no user authentication.

`Settings` loads the project `.env`, then `backend/.env` if present; process environment variables take precedence. The production database URL must use the `postgresql+psycopg` driver. API readiness returns 503 for an unavailable database or a migration revision that does not match the code; liveness remains independent of PostgreSQL.

Stop the API with Ctrl+C. Stop the development DB with `docker compose down` from the repository root. This preserves its named volume. Do not add `-v` unless you intend to discard local inventory data.

## React frontend

For hot-reload development, Vite uses [http://127.0.0.1:5173](http://127.0.0.1:5173). It can connect to either a host API or the container API at port 8000. The complete container application uses [http://127.0.0.1:3000](http://127.0.0.1:3000).

For a fresh checkout, use Node 22 and install the locked dependencies:

```powershell
# From stockflow/.
. ..\Enter-Project.ps1
Set-Location frontend
npm.cmd ci
```

Start the API with `scripts/start-backend.ps1` in one PowerShell terminal. In another terminal, from `stockflow/`:

```powershell
& .\scripts\start-frontend.ps1
```

The backend helper runs without automatic reload by default. Use `& .\scripts\start-backend.ps1 -Reload` for interactive backend development; restart it after source changes otherwise. Both helpers stay in the foreground when you run them yourself; Ctrl+C stops the corresponding server. A busy port means an existing server must be stopped or reused.

The Vite server binds to loopback port 5173 and proxies relative `/api` requests to `http://127.0.0.1:8000`. `STOCKFLOW_API_TARGET` selects a different API for isolated development tests. Production Nginx takes `API_UPSTREAM` and `NGINX_RESOLVER` at container startup; these are not embedded into JavaScript.

Workspace navigation: Overview, Products, and Stock activity. A product's name/history action opens its full paginated ledger. Activity shows the 10 latest movements across the workspace, with links to full product history. Low-stock navigation uses server-side filtering across all catalog pages. Stock dialogs fetch the latest quantity, preview the result, prevent obvious overselling, and preserve entered values if a concurrent change causes an API conflict.

The current workspace displays amounts in **INR** and times in **IST**. This is a display convention; no currency conversion is performed. Monetary strings are passed directly to Intl formatting to preserve exact decimal values. Fonts are served from local bundled assets; their OFL licenses are included under `frontend/public/licenses/`.

## Frontend checks

```powershell
# From frontend/, with Node 22 on PATH.
npm.cmd test
npm.cmd run build
```

For the complete browser workflow checks, from `stockflow/`:

```powershell
# First run if the isolated Chromium binary is not installed:
& .\scripts\test-frontend.ps1 -InstallBrowser
# Later runs:
& .\scripts\test-frontend.ps1
```

This helper checks the unit tests/build, starts a disposable test database on 5433, API on 8001, and Vite on 5174, then runs Playwright in an isolated Chromium profile. It stops only its own QA servers and removes the disposable DB afterward. Development inventory on port 5432 is unaffected. Run it separately from the backend test helper because they share the disposable test DB/port.

The frontend includes repeatable browser checks for create/edit, receive/issue and insufficient stock, deletion/cancellation, duplicate SKUs and failed-save retry, cross-page filters/pagination, stale-stock conflicts, picker/activity/history, and mobile navigation. Read [frontend verification](docs/FRONTEND_VERIFICATION.md) for results and screenshots. Generated browser caches, traces, and reports are ignored by Git.

## Container checks

```powershell
# From stockflow/, with Node 22, frontend dependencies, and Chromium installed:
& .\scripts\test-containers.ps1
```

This starts the same images in an isolated Compose project on 3001/8002/5434, verifies non-root execution, migrations, API behavior, all 8 browser workflows, backend replacement, and persistence after `down`/`up`, then removes only its disposable QA volume. See [verification details](docs/CONTAINERS.md).

## CI, security, and release images

The image workflow is [.github/workflows/ci.yml](.github/workflows/ci.yml). Application changes trigger tests/builds/scans; pull requests have no publication credentials. A separate publish job runs only for successful source pushes to `main`, using the job's `GITHUB_TOKEN` with `packages: write`; no personal token is committed or required for CI publishing. Manual dispatch validates without publishing. Helm/GitOps/monitoring-only changes use the separate chart workflow and do not build another image release. Both Applications use `helm/stockflow/values-release.yaml` to promote an already successful source SHA; a values commit and the source commit are different commits.

Both images must pass `trivy image --severity HIGH,CRITICAL --exit-code 1`. Unfixed findings are included and there are no CVE suppressions. Test results, JSON scan reports, and publication receipts are saved as workflow artifacts. The publish job verifies a saved archive checksum and scanned image IDs before tagging/pushing; it never rebuilds or runs the downloaded images.

Release names use the full source SHA, with a lowercase owner:

```text
ghcr.io/pyush269/stockflow-backend:<full-source-sha>
ghcr.io/pyush269/stockflow-frontend:<full-source-sha>
```

See [CI/security operation and evidence](docs/CI_SECURITY.md), including the actual run link, image digests, security remediation, and package access requirements. GHCR packages initially default to private; public repository visibility alone does not make them anonymously pullable.

Repeat the backend tests on Linux without host Python or development data access:

```powershell
docker compose -f compose.ci.yml up --build --abort-on-container-exit --exit-code-from backend-tests
docker compose -f compose.ci.yml down
```

## GitOps and monitoring

The [ArgoCD runbook](argocd/README.md) describes the restricted AppProject, manual first sync, automated reconciliation, SHA promotion, and compatible rollback. ArgoCD owns its application resources; Actions publishes images. Secrets and namespaces are prepared separately. The production Application is prepared but has not been applied to AWS.

The [monitoring runbook](monitoring/README.md) contains canonical chart values, the provisioned six-panel Grafana dashboard, and bounded read traffic commands. [Local monitoring evidence](docs/OBSERVABILITY.md) records 8,780 requests without failures, populated queries, and HPA scaling 2 -> 3 -> 2. The longer check found and corrected Grafana sidecar OOMs; the replacement pod stayed healthy throughout the successful experiment. Local performance is not a cloud benchmark.

The [PDF slides](demo/slides.pdf) cover the implemented architecture and explicitly mark AWS deployment pending. [Recording guidance](demo/RECORDING.md) lists the actual cloud evidence still needed. The video has not been recorded.

## API contract

| Method | Path | Behavior |
|---|---|---|
| GET | `/health` | Process health |
| GET | `/ready` | DB connection, migration revision, and table readiness |
| GET | `/metrics` | Prometheus HTTP metrics |
| GET/POST | `/api/products` | Paginated catalog / create zero-stock product |
| GET | `/api/products/categories` | Case-insensitive category choices across the whole catalog |
| GET/PUT/DELETE | `/api/products/{id}` | Read / replace editable metadata / delete unused product |
| GET/POST | `/api/products/{id}/movements` | Paginated history / stock-in or stock-out |
| GET | `/api/dashboard` | Inventory totals, low-stock list, recent movements |

Catalog query parameters: `q`, `category`, `stock_status` (`healthy`, `low`, or `out`), `limit` (1–100), and `offset` (>=0). `low` includes zero stock and the reorder boundary; `healthy` is above the reorder level; `out` is exactly zero. Pages return `{items, total, limit, offset}`. Stock history uses the same pagination fields and newest-first ordering. Dashboard lists are limited to ten items each; total counters cover the whole catalog.

Product example:

```json
{"sku":"HUB-001","name":"USB-C Hub","category":"Electronics","unit_price":"19.99","reorder_level":5}
```

`POST` starts quantity at zero. `PUT` replaces editable metadata using the same schema; include all fields whose values you want to preserve. Quantity is forbidden in both request types, and unknown fields are rejected. Decimal amounts are returned as JSON strings to preserve precision.

Movement examples:

```json
{"movement_type":"IN","quantity":10,"note":"Opening stock"}
```

```json
{"movement_type":"OUT","quantity":3,"note":"Customer order"}
```

The movement response contains `{product, movement}`, including the updated quantity. Issuing 8 more units now returns 409 and leaves quantity 7 and two ledger entries. Correct mistakes using a compensating movement rather than modifying history. A product with any movement history remains undeletable even when its current stock is zero.

Success codes: 201 for creates/movements, 200 for reads/updates, and empty 204 for deletion. Failures use:

```json
{"error":{"code":"insufficient_stock","message":"Requested quantity exceeds available stock"}}
```

Validation errors return 422 with field details; missing products return 404; duplicate SKUs, insufficient stock, stock overflow, and protected deletion return 409. Unavailable database operations return a sanitized 503 response.

## Tests

The suite uses **real PostgreSQL**, on a separate port/database with disposable storage. It never falls back to SQLite or silently skips database tests. It refuses to run destructive fixtures unless `TEST_DATABASE_URL` names `stockflow_test`. Do not point it at a database you need to keep, even if that database has the allowed name. Run sequentially; the current truncate-per-test fixture is not an xdist setup.

```powershell
# From stockflow/.
. ..\Enter-Project.ps1
docker compose -f compose.test.yml up -d --wait
$env:TEST_DATABASE_URL = 'postgresql+psycopg://stockflow_test:stockflow_test_only@127.0.0.1:5433/stockflow_test'
Set-Location backend
& .\.venv\Scripts\python.exe -m pytest -v
```

Or run `& .\scripts\test-backend.ps1` from `stockflow/`. It starts only the disposable test DB, runs the suite, and removes that test service afterward. Development data is unaffected. The public test-only password is not a deployment credential.

Checks include migration upgrade/downgrade on the empty test DB, `alembic check` for model/schema drift, actual DB constraints, API validation, and both requests visibly waiting on a PostgreSQL row lock before a simultaneous stock-out test completes.

The installed Starlette TestClient emits an upstream warning about HTTPX deprecation; the tests run successfully with the pinned HTTPX version. See [verification results](docs/VERIFICATION.md) for the recorded run and limits.

## Project structure and next stage

```text
backend/app/                API, schemas, models, transactional inventory service
backend/alembic/            Versioned schema migrations
backend/tests/              API and PostgreSQL integration coverage
scripts/                    Local startup and test helpers
frontend/                   React/Vite workspace, self-hosted assets, frontend/browser tests
docker-compose.yml          Complete application, migration job, persistent PostgreSQL
compose.test.yml            Separate disposable PostgreSQL test service
compose.ci.yml              Isolated Linux backend test image and PostgreSQL
.github/workflows/ci.yml    Tests, strict scans, archive verification, GHCR release
.github/workflows/terraform.yml  Credential-free Terraform validation and mock tests
.github/workflows/helm.yml   Chart checks and disposable Kubernetes runtime verification
terraform/                  VPC, EKS managed nodes/add-ons, IAM, logs, locked providers
helm/stockflow/              App chart, migrations, storage, HPA, Ingress, ServiceMonitor
k8s/bootstrap/              Pinned controllers, monitoring, ArgoCD, and bootstrap runbook
argocd/                     Restricted project and local/production Applications
monitoring/                 Canonical chart values and provisioned dashboard JSON
demo/                       PDF slides, editable content, recording checklist
docs/WORKFLOW.md            Full staged implementation plan
docs/VERIFICATION.md        Completed checks and remaining work
docs/CONTAINERS.md          Prompt 3 checks, local operation, troubleshooting
docs/CI_SECURITY.md         Prompt 4 workflow, reports, digests, access requirements
docs/INFRASTRUCTURE.md      Prompt 5 real plan review, Sydney prices, findings, cleanup
docs/HELM.md                Prompt 6 local evidence and remaining cloud checks
docs/GITOPS_VERIFICATION.json  Actual local release, rollback, and recovery results
docs/OBSERVABILITY.md       Load, live metrics, scaling, and Grafana memory correction
```

Next cloud step, when deployment is authorized: refresh the plan/operator IP, apply the reviewed infrastructure, bootstrap controllers, and repeat the Helm, GitOps, ALB/storage, and monitoring checks on EKS. Update the slides with real cloud evidence, record the mandatory walkthrough, and clean up after evaluation. Follow [the checklist](docs/DEPLOYMENT_CHECKLIST.md) and preserve actual evidence as each stage passes.
