# StockFlow presentation content

Prepared 15 October 2026. This is editable content and speaker guidance for the
PDF deck, not proof of an AWS deployment. Replace pending cloud evidence after
deploying and verifying EKS. Do not present local screenshots as AWS screenshots.

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

Visual: `docs/screenshots/container-overview-qa.png`, an actual local screenshot.
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

- Terraform plan: 59 additions, no changes or destroys.
- One `m7i-flex.large` worker; two frontend/backend Pods each.
- Estimated infrastructure: $0.29/hour; illustrative full demo: $0.33/hour.
- Variable usage adds cost. A single worker has no worker redundancy.

Visible status: AWS deployment pending. Replace with actual VPC/EKS evidence
after approval, including real node readiness.
Speaker note: Explain NAT, EKS, worker, public IPv4, and storage costs. Credits
pay eligible usage; leaving infrastructure running continues consuming them.
Source: `docs/INFRASTRUCTURE.md`, `docs/INFRASTRUCTURE_REVIEW.json`.

## 7. Kubernetes and Helm

- Two frontend and backend replicas with probes and resource bounds.
- PostgreSQL StatefulSet retains its PVC.
- A migration Job completes before application schema readiness.
- Ingress routes `/` and `/api`; HPA scales backend Pods from 2 to 3.

Visual: local Helm evidence now; actual `helm list`, gp3 PVC, and ALB health later.
Speaker note: The local Helm install, upgrade, and DB pod replacement preserved
stock. EBS/IRSA and public ALB behavior still need real AWS verification.
Source: `docs/HELM.md`, `docs/HELM_VERIFICATION.json`.

## 8. GitOps release and rollback

Green source CI → release-values commit → ArgoCD reconciliation

- ArgoCD owns the chart's resources; Actions publishes images.
- Initial sync is manual; automation follows health verification.
- Both image tags change together in `values-release.yaml`.
- Reverting the promotion commit restores a compatible image release.

Visual: real ArgoCD Synced/Healthy view and recorded release/rollback evidence.
Speaker note: Image rollback does not undo database migrations. The first demo
uses application releases with the same schema. Show actual Git revisions.
Source: `argocd/README.md`, local verification report when generated.

## 9. Monitoring and scaling

- Prometheus discovers backend metrics through ServiceMonitor.
- Grafana shows API request rate, p95 latency, errors, and backend resources.
- Bounded traffic exercises only read endpoints.
- HPA observations show what actually happened under that traffic.

Visual: `docs/screenshots/stockflow-grafana-local.png` after verification.
Speaker note: Quote the saved load result and replica observations exactly. Do
not infer throughput, availability, or cloud performance from this local test.
Source: monitoring JSON and runtime verification report when generated.

## 10. Recovery and lessons

- Backend pod replacement restores the declared replica count.
- PVC reuse preserves database inventory after a PostgreSQL pod restart.
- ArgoCD migration hooks must run during sync.
- Grafana sidecars needed larger memory limits during the longer check.

Speaker note: Show the recorded recovery, explain the diagnosed issues, and
distinguish Pod recovery from a single worker failure that interrupts the demo.

## 11. Evaluation and cleanup

- Final cloud checks: EKS, EBS, ALB, ArgoCD, and dashboard evidence.
- The public URL works on other devices while AWS resources remain running.
- Keep resources for evaluation unless the instructor permits recording only.
- Back up required data, remove the ALB/workloads, then destroy Terraform.

Speaker note: Source code and evidence remain after destroy; the public URL
stops working. A fresh local checkout can still run with Docker Compose.
Save real destroy output after evaluation. Do not mark cleanup complete early.

## Deck format

The rubric accepts PDF slides. `demo/slides.pdf` uses this content and actual
local evidence on a 16:9 canvas. `demo/build-slides.py` generates the PDF from the
saved verification reports. Regenerate it after cloud verification so it reflects
the final EKS/ALB results. Keep this editable content for rehearsal and updates.
