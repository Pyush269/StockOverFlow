# StockFlow

Inventory management with a product catalog, stock receipts/issues, an append-only API ledger, and low-stock reporting. Built for the DevSecOps capstone using React/FastAPI/PostgreSQL and the planned EKS/Helm/ArgoCD delivery architecture.

## Current stage

**Foundation and backend implemented.** The React interface, application Docker images, CI/CD, Terraform, Helm, GitOps, and monitoring deployment are subsequent stages. The current `docker-compose.yml` starts the development database only; it does not yet start a complete frontend/backend stack.

- Product CRUD with normalized unique SKUs, search/category filters, and pagination.
- Transactional stock-in/stock-out with PostgreSQL row locks.
- Insufficient-stock and integer-overflow protection.
- Read-only stock history; products with history cannot be deleted.
- Dashboard totals, exact decimal inventory value, low-stock results, and recent movements.
- Alembic migrations, health/schema readiness, Prometheus HTTP metrics, explicit development CORS origins.
- PostgreSQL integration tests, including deterministic lock contention, rollback after a failed ledger write, migration round-trip, and database constraints.

## Architecture

```text
Current: FastAPI -> PostgreSQL 16
Next:    React/Nginx -> FastAPI -> PostgreSQL
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

## API contract

| Method | Path | Behavior |
|---|---|---|
| GET | `/health` | Process health |
| GET | `/ready` | DB connection, migration revision, and table readiness |
| GET | `/metrics` | Prometheus HTTP metrics |
| GET/POST | `/api/products` | Paginated catalog / create zero-stock product |
| GET/PUT/DELETE | `/api/products/{id}` | Read / replace editable metadata / delete unused product |
| GET/POST | `/api/products/{id}/movements` | Paginated history / stock-in or stock-out |
| GET | `/api/dashboard` | Inventory totals, low-stock list, recent movements |

Catalog query parameters: `q`, `category`, `limit` (1–100), and `offset` (>=0). Pages return `{items, total, limit, offset}`. Stock history uses the same pagination fields and newest-first ordering. Dashboard lists are limited to ten items each; total counters cover the whole catalog.

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
docker-compose.yml          Persistent development PostgreSQL
compose.test.yml            Separate disposable PostgreSQL test service
docs/WORKFLOW.md            Full staged implementation plan
docs/VERIFICATION.md        Completed checks and remaining work
```

Next implement the React dashboard, catalog/forms, movement dialogs, and history against this API. Then complete the full non-root Docker Compose application stack, CI/security/GHCR, Terraform/EKS, Helm/ArgoCD, monitoring, and submission artifacts according to [the workflow](docs/WORKFLOW.md). Take real evidence and make meaningful incremental commits as each stage passes.
