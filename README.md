# StockFlow

[![StockFlow CI](https://github.com/Pyush269/StockOverFlow/actions/workflows/ci.yml/badge.svg)](https://github.com/Pyush269/StockOverFlow/actions/workflows/ci.yml)
[![Terraform validation](https://github.com/Pyush269/StockOverFlow/actions/workflows/terraform.yml/badge.svg)](https://github.com/Pyush269/StockOverFlow/actions/workflows/terraform.yml)
[![Helm validation](https://github.com/Pyush269/StockOverFlow/actions/workflows/helm.yml/badge.svg)](https://github.com/Pyush269/StockOverFlow/actions/workflows/helm.yml)

Inventory management with a searchable product catalog, stock receipts and issues,
a transaction ledger, and low-stock reporting. Deployed and verified on AWS EKS
in Sydney (`ap-southeast-2`).

**[Live application](http://k8s-stockflo-stockflo-96a126ddd5-1324338338.ap-southeast-2.elb.amazonaws.com)**
| **[Full walkthrough video](demo/stockflow-walkthrough-silent.mp4)**
| **[Presentation slides](demo/slides.pdf)**
| **[Grading evidence](docs/GRADING_EVIDENCE.md)**

The video is 12:13, silent, and includes captions. It presents the 11 slides first,
then the website, code, actual push and completed CI, Terraform/AWS, ArgoCD,
Kubernetes, Prometheus Targets, and Grafana. [Chapter times](demo/WALKTHROUGH.md).

## Features and design

- Product CRUD, unique SKUs, search, category and stock filters, and pagination.
- Stock-in/out operations and an append-only movement ledger in one PostgreSQL
  transaction. Row locks prevent concurrent stock-outs from overselling.
- Dashboard totals, exact decimal inventory value, low-stock alerts, and history.
- Responsive React screens, accessible dialogs, validation, and API error handling.
- Alembic migrations, database/schema readiness checks, and Prometheus metrics.

## Architecture

```text
Browser -> AWS ALB -> /     -> React / Nginx
                  -> /api  -> FastAPI -> PostgreSQL / encrypted EBS PVC

Git push -> GitHub Actions -> tests -> Docker builds -> Trivy gates -> GHCR
Release SHA in Git -> ArgoCD -> Helm-rendered resources on AWS EKS
FastAPI /metrics -> Prometheus -> Grafana
Terraform -> VPC, subnets, NAT, EKS, worker, IAM/Pod Identity, encryption/logs
```

**Stack:** Python 3.12, FastAPI, SQLAlchemy, Alembic, PostgreSQL 16, React 19,
Vite 8, Nginx, Docker Compose, GitHub Actions, GHCR, Trivy, Terraform,
Kubernetes/EKS, Helm, ArgoCD, Prometheus, and Grafana.

```text
backend/       API, migrations, PostgreSQL tests, Dockerfile
frontend/      React application, unit/browser tests, Dockerfile
.github/       Application, Terraform, and Helm validation workflows
terraform/     AWS infrastructure and provider lockfile
helm/          Application chart and environment/release values
k8s/           Namespace and cluster bootstrap configuration
argocd/        GitOps Application and AppProject
monitoring/    Prometheus/Grafana values and provisioned dashboard
scripts/       Build, test, deployment, and verification commands
docs/          Grading evidence, cloud results, infrastructure notes
demo/          Full video, captions, chapter guide, and PDF slides
```

## Run locally

Prerequisite: Docker Desktop with Linux containers and Docker Compose.
No host Python or Node installation is needed for the complete stack.

For a fresh checkout:

```powershell
git clone https://github.com/Pyush269/StockOverFlow.git
Set-Location StockOverFlow
Copy-Item .env.example .env
```

Edit `.env`: choose a long alphanumeric password and put the **same value** in
`POSTGRES_PASSWORD` and the password component of `DATABASE_URL`. For an existing
installation, retain its `.env` and database password.

```powershell
docker compose config --quiet
docker compose up --build -d --wait
docker compose ps --all
```

Open [the application](http://localhost:3000), [Swagger UI](http://localhost:8000/docs),
[health](http://localhost:8000/health), [readiness](http://localhost:8000/ready), and
[metrics](http://localhost:8000/metrics). Local ports bind to loopback.
The migration job should exit with code 0; frontend, backend, and database should
be healthy. Both application images run as non-root users.

```powershell
docker compose logs migrate backend frontend
docker compose down
# Restart with the same inventory:
docker compose up -d --wait
```

`down` preserves the database volume. `down --volumes` deletes local inventory.
Schema changes run through Alembic; the API does not create tables at startup.

## Tests

Run all 49 backend tests against a separate temporary PostgreSQL database:

```powershell
docker compose -f compose.ci.yml up --build --abort-on-container-exit --exit-code-from backend-tests
docker compose -f compose.ci.yml down
```

The fixtures reject database names other than `stockflow_test`. Coverage includes
CRUD, validation, ledger constraints, insufficient stock, concurrency, rollback,
and migration round trips. [Actual verbose results](docs/evidence/pytest-verbose.txt).

For the 11 frontend unit tests and production build, install Node 22:

```powershell
Set-Location frontend
npm ci
npm test
npm run build
```

Eight browser workflows are defined in [frontend/e2e](frontend/e2e/).
Windows helpers in `scripts/test-frontend.ps1` and `scripts/test-containers.ps1`
run them against isolated services. They require the frontend dependencies,
Playwright Chromium, and a Python 3.12 environment at `backend/.venv` installed
from `backend/requirements-dev.lock.txt`.

## CI/CD and security

Every push to `main` runs [StockFlow CI](.github/workflows/ci.yml):

1. Apply migrations to isolated PostgreSQL, run `pytest -v`, run frontend unit
   tests, and build the frontend.
2. Build both Docker images once. Trivy scans their OS packages and application
   dependencies; any HIGH or CRITICAL finding blocks publication, including
   unfixed findings.
3. Verify the release archive and image identities, then publish the exact
   scanned images to GHCR with the full Git commit SHA as the tag.

PR jobs have no package write permission. The publication job uses GitHub's
short-lived `GITHUB_TOKEN`. Credentials and environment files are excluded from Git.
[Recorded successful run](https://github.com/Pyush269/StockOverFlow/actions/runs/38867618119).

The [Terraform workflow](.github/workflows/terraform.yml) checks formatting,
locked-provider initialization, validation, and mocked infrastructure tests.
The [Helm workflow](.github/workflows/helm.yml) validates chart/GitOps contracts
and exercises an isolated Kubernetes install/upgrade. Neither workflow receives
AWS credentials or provisions cloud resources.

## Terraform infrastructure

[terraform/](terraform/) provisions a VPC with two public and two private subnets
across two availability zones, one NAT gateway, an EKS cluster, and one private
`m7i-flex.large` worker. It includes encrypted storage, logs, and scoped EKS Pod
Identity roles for the CNI, EBS CSI driver, and Load Balancer Controller.

The existing deployment uses profile `stockflow` in Sydney. A fresh deployment
requires AWS sign-in, the tools on PATH, and a reviewed `terraform.tfvars` based
on [the example](terraform/terraform.tfvars.example):

```powershell
$env:AWS_PROFILE = 'stockflow'
$env:AWS_REGION = 'ap-southeast-2'
terraform -chdir=terraform init -lockfile=readonly
terraform -chdir=terraform validate
terraform -chdir=terraform plan -out=stockflow-reviewed.tfplan
# Review the plan, costs, and target project before applying:
terraform -chdir=terraform apply stockflow-reviewed.tfplan
```

[Infrastructure details, cost review, and cleanup](docs/INFRASTRUCTURE.md).
Real credentials, tfvars, binary plans, kubeconfig, and state stay outside Git.

## Kubernetes, Helm, and GitOps

Install operator dependencies with `python -m pip install -r requirements-ops.txt`.
After infrastructure is applied:

```powershell
python scripts/configure-eks.py
$env:KUBECONFIG = Join-Path $PWD '.logs/eks.kubeconfig'
.\scripts\bootstrap-cluster.ps1 -Context stockflow-eks-sydney
```

Bootstrap installs the pinned controllers, metrics server, ArgoCD, Prometheus,
and Grafana. [Bootstrap and manual Helm commands](k8s/bootstrap/README.md).
The application chart defines two frontend and two backend replicas, ClusterIP
Services, a PostgreSQL StatefulSet/PVC, migration hooks, ALB Ingress, and HPA.
Ingress routes `/` to the frontend and `/api` to the backend.

Production is reconciled by ArgoCD using [application.yaml](argocd/application.yaml)
and the chart's `values-prod.yaml` plus `values-release.yaml`.
[Initial sync, promotion, and rollback](argocd/README.md).
Publishing an image does not deploy it: a release-values commit selects the
published SHA; reverting that commit performs a compatible image rollback.

```powershell
kubectl --context stockflow-eks-sydney -n stockflow get pods,svc,ingress,pvc,hpa
kubectl --context stockflow-eks-sydney -n argocd get application stockflow
```

## Observability

The chart's ServiceMonitor connects FastAPI metrics to Prometheus.
[monitoring/values.yaml](monitoring/values.yaml) configures the monitoring stack;
[stockflow.json](monitoring/stockflow.json) provisions six Grafana panels for
request rate, latency, errors, CPU, memory, and Ready backend replicas.

Use separate terminals for each localhost port-forward:

```powershell
kubectl --context stockflow-eks-sydney -n monitoring port-forward svc/monitoring-kube-prometheus-prometheus 9090:9090
kubectl --context stockflow-eks-sydney -n monitoring port-forward svc/monitoring-grafana 3002:80
```

Open [Prometheus Targets](http://localhost:9090/targets) and
[Grafana](http://localhost:3002/d/stockflow-overview). Use the generated Grafana
admin credentials locally. [Monitoring commands and queries](monitoring/README.md).
[Actual cloud verification](docs/CLOUD_VERIFICATION.md).

## Deployment limits and evaluation

This is a short capstone deployment: public HTTP with demo inventory, no user
authentication, one worker, and single-instance PostgreSQL. It is not configured
for production availability or disaster recovery. PostgreSQL uses persistent
EBS; monitoring history and UI-only dashboard edits are ephemeral.
Three Terraform configuration findings remain documented in
[the infrastructure review](docs/INFRASTRUCTURE.md#configuration-scan-findings).
They are separate from the passing image vulnerability gates.

Submit [this repository](https://github.com/Pyush269/StockOverFlow) through
[the instructor's form](https://forms.gle/XWAP1vAumDJgAPM1A).
AWS remains running for evaluation and consumes credits. After evaluation,
complete the documented cleanup and save the actual Terraform destroy screenshot;
that result has not yet been collected.
