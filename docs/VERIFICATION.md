# Foundation and backend verification

Verified on 15 October 2026 (IST), Windows/Python 3.12.10, using PostgreSQL 16 containers.

This records Prompt 1. Prompt 2 adds the React frontend and two backend filter tests; see [current frontend verification](FRONTEND_VERIFICATION.md) and [README](../README.md) for the latest state.

## Completed

- Created a separate local StockFlow Git repository and backend virtual environment.
- Implemented product CRUD, normalized unique SKUs, literal-safe search, category filtering, and bounded pagination.
- Implemented stock receipts/issues and a read-only API ledger. Product row locks serialize competing quantity changes and deletion; one transaction covers inventory and movement writes.
- Enforced insufficient-stock/overflow protection, nonnegative inventory, valid movement types/quantities, and history-preserving delete behavior.
- Implemented dashboard totals/low-stock/recent movements, exact Decimal amounts, UTC timestamps, health/readiness, Prometheus metrics, and explicit CORS origins.
- Created the versioned Alembic schema without `create_all` during API startup.
- Pinned direct dependencies and recorded full runtime/development dependency locks.
- Created a persistent development database, an ignored local configuration with a generated password, and an independent disposable PostgreSQL test service.
- Added PowerShell startup/test helpers and saved the full project workflow.

## Automated results

**47 passed, 1 upstream deprecation warning.** Full output: [TEST_RESULTS.txt](TEST_RESULTS.txt).

Tests run through `scripts/test-backend.ps1`, which starts the isolated test service and removes it afterward. The suite verifies:

- API CRUD, SKU conflicts, request validation, pagination/search, deletion rules, and missing records.
- Receive 10, issue 3, reject 8: quantity stays 7 with two ledger entries.
- Injected failure after ledger insertion rolls back both pending inventory and movement writes.
- Two concurrent stock-out requests are observed waiting on PostgreSQL row locks. After release, exactly one succeeds, the other returns 409, and inventory remains nonnegative.
- Migration downgrade/upgrade against the disposable DB, model/schema parity, and database-level constraints.
- Empty/populated dashboard totals and the inclusive low-stock boundary.
- Live health independent of the DB; 503 readiness for an unreachable DB or stale migration revision.
- Prometheus HTTP metrics and allowed/denied CORS origins.

The warning comes from the installed Starlette TestClient's use of HTTPX. It does not represent a failed application test; the pinned TestClient/HTTPX combination was exercised successfully.

Additional checks: development `alembic upgrade head` and `alembic check` passed; Python source compiled; PowerShell helper files parsed successfully.

## Real HTTP verification

A temporary Uvicorn server was bound to `127.0.0.1:8000`, exercised through actual HTTP requests, then stopped. Results: [LIVE_API_RESULTS.json](LIVE_API_RESULTS.json).

- Health: UP; database/schema readiness: READY.
- Development database had zero products after the isolated tests completed.
- Created one demo USB-C Hub, received 10, issued 3, and rejected a further issue of 8 with HTTP 409.
- Confirmed quantity 7 and two movement entries after the rejected request.
- Swagger UI returned HTTP 200 and Prometheus HTTP metrics were present.

The demo product remains in the development database for the next stage. Its ID/SKU are in the result file. The development PostgreSQL service is left running; the disposable test service and temporary verification API were stopped. Start the API using `scripts/start-backend.ps1` to view the demo through `/docs`.

## Remaining stages and limits

- React frontend and browser-based inventory screens.
- Complete backend/frontend container images and one-command application Compose stack. Current development Compose starts PostgreSQL only.
- GitHub remote/account setup, CI, Trivy image scans, and GHCR publishing.
- Terraform, AWS infrastructure, cluster dependencies, Helm, ArgoCD, monitoring deployment, and scaling/rollback demonstrations.
- Submission screenshots, slide deck, and mandatory walkthrough video.

The backend currently has no user authentication and is configured for local loopback development. Full locks were generated on Windows; the Linux container stage must validate platform-specific dependencies. No AWS resources were created, no repository was published, and no cloud deployment has been claimed.

Implementation references: [PostgreSQL row locking](https://www.postgresql.org/docs/current/explicit-locking.html), [SQLAlchemy ORM](https://docs.sqlalchemy.org/en/21/orm/), [Alembic schema comparison](https://alembic.sqlalchemy.org/en/latest/autogenerate.html), and [FastAPI testing](https://fastapi.tiangolo.com/advanced/testing-dependencies/).
