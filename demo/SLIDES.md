# StockFlow presentation content

Updated 16 October 2026. Editable content and speaker guidance for the PDF deck. Cloud results and screenshots come from the verified EKS deployment; see `docs/CLOUD_VERIFICATION.md`. The complete silent walkthrough uses on-screen explanations and captions.

## 1. StockFlow

Inventory management with a stock movement ledger

Piyush · DevSecOps capstone

Speaker note: Show the application first. Explain that StockFlow tracks products,
receipts, issues, and low stock. Repository:
https://github.com/Pyush269/StockOverFlow

## 2. Inventory workflow

- Product catalog with search, categories, and pagination.
- Receipts and issues update inventory and append a movement record.
- Low-stock reporting uses the current database quantity.
- Products with movement history retain their ledger.

Visual: `docs/screenshots/stockflow-cloud-overview.png`, the actual public AWS application.
Speaker note: Receive 10, issue 3, then reject an issue of 8. Quantity stays 7.

## 3. Application architecture

React / Nginx → FastAPI → PostgreSQL 16

- Browser requests use relative `/api` paths.
- Alembic applies the schema before the API becomes Ready.
- PostgreSQL row locks serialize competing stock changes.
- Inventory and ledger writes share one database transaction.

Speaker note: Show `backend/app/main.py`, migrations, and the transaction tests.
Source: application code and `docs/CONTAINERS.md`.

## 4. Tests and local runtime

49 PostgreSQL backend tests · 11 frontend unit tests · 8 browser workflows

- Tests cover overselling, rollback, and concurrent stock issues.
- Disposable test databases keep development inventory separate.
- Docker Compose starts PostgreSQL, migration, backend, and frontend.
- Both application images run as non-root users.

Visual: actual green CI/test output; no invented benchmark.
Source: `docs/CI_RELEASE.json`, `docs/FRONTEND_VERIFICATION.md`.

## 5. CI and image security

Source commit → tests → image build → Trivy gate → GHCR publication

- HIGH/CRITICAL findings fail either application image's gate.
- Publication uses the same scanned image bytes.
- Both image tags use the full source commit SHA.
- Pull requests receive no registry publication credentials.

Speaker note: Open a successful main CI run, both scan artifacts, and both GHCR
tags. The Terraform configuration scan is a separate check with three documented
findings; do not call all security scans clean.
Source: `.github/workflows/ci.yml`, `docs/CI_SECURITY.md`.

## 6. AWS infrastructure and cost

Sydney · private worker · public ALB · persistent encrypted gp3 database disk

- Terraform applied successfully; final refreshed plan reports no changes.
- EKS ACTIVE; five ACTIVE add-ons and scoped Pod Identity service roles.
- One `m7i-flex.large` worker; two frontend/backend Pods each.
- Estimated infrastructure: $0.29/hour; illustrative full demo: $0.33/hour.
- Variable usage adds cost. A single worker has no worker redundancy.

Verified status: one Ready private EKS worker, encrypted gp3 storage, and an active public ALB with healthy frontend/API targets. The managed project blocked IAM OIDC creation, so supported EKS Pod Identity was used without changing organization policies.
Speaker note: Explain NAT, EKS, worker, public IPv4, and storage costs. Credits
pay eligible usage; leaving infrastructure running continues consuming them.
Source: `docs/INFRASTRUCTURE.md`, `docs/AWS_VERIFICATION.json`, and `docs/DEPLOYMENT_REVIEW_20261016.json`.

## 7. Kubernetes and Helm

- Two frontend and backend replicas with probes and resource bounds.
- PostgreSQL StatefulSet retains its PVC.
- A migration Job completes before application schema readiness.
- Ingress routes `/` and `/api`; HPA scales backend Pods from 2 to 3.

Visual: `docs/CLOUD_HELM_LIST.txt`, the actual cloud replicas/PVC report, and public ALB screenshot.
Speaker note: Cloud Helm install, upgrade/migration, and PostgreSQL replacement preserved quantity 7 on the same PVC. The disposable smoke release and test volume were removed before production GitOps.
Source: `docs/CLOUD_HELM_VERIFICATION.json`, `docs/AWS_VERIFICATION.json`.

## 8. GitOps release and rollback

Green source CI → release-values commit → ArgoCD reconciliation

- ArgoCD owns the chart's resources; Actions publishes images.
- Initial sync is manual; automation follows health verification.
- Both image tags change together in `values-release.yaml`.
- Reverting the promotion commit restores a compatible image release.

Visual: real ArgoCD Synced/Healthy view and recorded release/rollback evidence.
Speaker note: Image rollback does not undo database migrations. The first demo
uses application releases with the same schema. Show actual Git revisions.
Source: `argocd/README.md`, `docs/CLOUD_RUNTIME_VERIFICATION.json`, and `docs/screenshots/stockflow-argocd-cloud.png`.

## 9. Monitoring and scaling

- Prometheus discovers backend metrics through ServiceMonitor.
- Grafana shows API request rate, p95 latency, errors, and backend resources.
- Bounded traffic exercises only read endpoints.
- HPA observations show what actually happened under that traffic.

Visual: `docs/screenshots/stockflow-grafana-cloud.png`, the actual cloud dashboard.
Speaker note: Quote the saved load result and replica observations exactly. Do
not treat this client-side demo load as a production benchmark.
Source: `docs/CLOUD_OBSERVABILITY_VERIFICATION.json`.

## 10. Recovery and lessons

- Backend pod replacement restores the declared replica count.
- PVC reuse preserves database inventory after a PostgreSQL pod restart.
- ArgoCD migration hooks must run during sync.
- Managed project policy required EKS Pod Identity instead of IAM OIDC.
- Actual one-worker capacity fits the demo but has limited pod headroom.

Speaker note: Show the recorded recovery, explain the diagnosed issues, and
distinguish Pod recovery from a single worker failure that interrupts the demo.

## 11. Evaluation and cleanup

- Cloud checks passed: EKS, EBS, ALB, ArgoCD, dashboard, and recovery evidence.
- The silent walkthrough includes actual AWS Console views.
- The public URL works on other devices while AWS resources remain running.
- Keep resources for evaluation unless the instructor permits recording only.
- Back up required data, remove the ALB/workloads, then destroy Terraform.

Speaker note: Source code and evidence remain after destroy; the public URL
stops working. A fresh local checkout can still run with Docker Compose.
Save real destroy output after evaluation. Do not mark cleanup complete early.

## Deck format

The rubric accepts PDF slides. `demo/slides.pdf` uses this content and actual
cloud evidence on a 16:9 canvas. `demo/build-slides.py` generates the PDF from the
saved verification reports. Regenerate it from the verified cloud reports when evidence changes. Keep this editable content for rehearsal and updates.

Final cloud load: 4,601 GET requests in 120.78 seconds, 0 failures; HPA peak Ready replicas 3. This is the measured client workload, not the configured RPS ceiling.
