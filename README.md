# StockFlow

Inventory management with a product catalog, stock receipts/issues, an append-only API ledger, and low-stock reporting. Built for the DevSecOps capstone using React/FastAPI/PostgreSQL and the planned EKS/Helm/ArgoCD delivery architecture.

## Current stage

**Foundation, backend, and React frontend implemented (Prompts 1 and 2).** Application Docker images, CI/CD, Terraform, Helm, GitOps, and monitoring deployment are subsequent stages. The current `docker-compose.yml` starts the development database only; the API and frontend currently run as local development processes.

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
Current: React/Vite -> /api proxy -> FastAPI -> PostgreSQL 16
Next:    React/Nginx container -> FastAPI container -> PostgreSQL
Later:   GitHub Actions -> Trivy -> GHCR -> Git release values -> ArgoCD/Helm -> AWS EKS
```

The backend never creates tables on startup. Apply Alembic migrations before starting it. Stock changes and ledger inserts share a single transaction. All movement, metadata update, and product delete operations acquire the same product row lock, preventing competing issues from overselling. The database also enforces nonnegative inventory and restricts deletion of referenced products.

## Local development on this computer

Prerequisites: Python 3.12, Docker Desktop with Linux containers, and Docker Compose. Tool installation details live in the parent Capstone folder.

From PowerShell in `Capstone\stockflow`:

```powershell
# Use the existing Capstone launcher to expose Docker and Python if needed.
. ..\Enter-Project.ps1

# Already prepared during initial implementation. For a fresh checkout:
python -m venv backend/.venv
& .\backend\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.lock.txt
```

StockFlow has its own environment at `backend/.venv`; it does not use the reference application's installed dependencies. `requirements.txt` pins direct runtime dependencies; `requirements.lock.txt` locks the installed runtime dependency set. The corresponding development files include pytest/TestClient dependencies. The generated locks were verified on Windows/Python 3.12; validate platform-specific wheels and refresh a suitable lock during the Linux container stage.

For a fresh checkout, copy `.env.example` to `.env` and replace the password in **both** `POSTGRES_PASSWORD` and `DATABASE_URL`. Use the same value. This checkout already has an ignored `.env` with a generated local password. URL-encode special password characters when constructing database URLs; a long alphanumeric value avoids that issue.

```powershell
# From stockflow/; Docker Desktop must be running.
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

The frontend is available at [http://127.0.0.1:5173](http://127.0.0.1:5173). Both that frontend and the API must be running for inventory operations. The current implementation session leaves both local servers running.

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

The Vite server binds to loopback port 5173 and proxies relative `/api` requests to `http://127.0.0.1:8000`. `STOCKFLOW_API_TARGET` can select a different API for an isolated local test server; it is a development-server setting, not a client-side secret or production configuration. Production routing is part of Prompt 3.

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
docker-compose.yml          Persistent development PostgreSQL
compose.test.yml            Separate disposable PostgreSQL test service
docs/WORKFLOW.md            Full staged implementation plan
docs/VERIFICATION.md        Completed checks and remaining work
```

Next complete **Prompt 3: the non-root Docker Compose application stack**, followed by CI/security/GHCR, Terraform/EKS, Helm/ArgoCD, monitoring, and submission artifacts according to [the workflow](docs/WORKFLOW.md). Take real evidence and make meaningful incremental commits as each stage passes.
