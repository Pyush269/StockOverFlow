# Grading evidence index

StockFlow is an inventory application with its own domain, source, and business
rules. The DevSecOps architecture follows the course pattern. This page maps the
[instructor's rubric](https://github.com/Nency-Ravaliya/devsecops-python/blob/main/GRADING.md)
to concrete source and evidence. It does not predict the instructor's score.

## M1 — Application

- [FastAPI application and `/health`](../backend/app/main.py),
  [product GET/POST/PUT/DELETE routes](../backend/app/routes/products.py),
  [stock movement routes](../backend/app/routes/movements.py), and
  [dashboard routes](../backend/app/routes/dashboard.py).
- [Alembic migration](../backend/alembic/versions/0001_inventory.py),
  [backend dependencies](../backend/requirements.txt), and
  [React frontend](../frontend/src/).
- [Cloud website](screenshots/stockflow-cloud-overview.png),
  [mobile layout](screenshots/stockflow-cloud-mobile.png), and
  [local browser](screenshots/stockflow-localhost-3000.png).
- [Actual HTTP verification](LIVE_API_RESULTS.json) and
  [cloud runtime verification](CLOUD_RUNTIME_VERIFICATION.json).

## M2 — Tests

- [Test suite](../backend/tests/), [pytest configuration](../backend/pytest.ini),
  and [isolated database fixtures](../backend/tests/conftest.py).
- [Actual verbose pytest execution](screenshots/stockflow-pytest-verbose.png):
  49 passing backend tests, with [all verbose test results](evidence/pytest-verbose.txt).
  The tests cover multiple endpoints, database
  constraints, migration parity, concurrent stock-outs, and transaction rollback.
- The fixture refuses to truncate any database other than `stockflow_test`.
  [Linux test setup](../compose.ci.yml) uses a separate temporary PostgreSQL service.
- [Frontend tests](FRONTEND_TEST_RESULTS.txt) cover 11 unit tests; the saved
  [browser checks](FRONTEND_VERIFICATION.md) cover eight workflows.

## M3 — Git and GitHub

- Public repository: [Pyush269/StockOverFlow](https://github.com/Pyush269/StockOverFlow).
- [Commit history screenshot](screenshots/stockflow-git-history.png) shows more
  than ten meaningful commits. [Full history](https://github.com/Pyush269/StockOverFlow/commits/main/).
- [.gitignore](../.gitignore) excludes local credentials/configuration, Python
  caches, environments, dependencies, Terraform state, and private logs.
- The repository URL still needs to be submitted through the instructor's form.

## M4 — Docker

- [Backend Dockerfile](../backend/Dockerfile): runtime UID/GID `10001:10001`.
- [Frontend Dockerfile](../frontend/Dockerfile): Node build stage, unprivileged
  Nginx runtime, UID/GID `101:101`.
- [Complete Compose stack](../docker-compose.yml),
  [actual `up --build` execution](screenshots/stockflow-compose-startup.png), and
  [browser at localhost:3000](screenshots/stockflow-localhost-3000.png).
- [Container verification](CONTAINERS.md) records startup order, health checks,
  routing, non-root operation, and persistent inventory.

## M5 — CI/CD

- [Application workflow](../.github/workflows/ci.yml) runs on every main push.
  Tests gate image builds; failures block publication. Both frontend and backend
  images use full source commit SHA tags.
- [Successful recorded pipeline](https://github.com/Pyush269/StockOverFlow/actions/runs/38867618119)
  and [successful documentation-only push](https://github.com/Pyush269/StockOverFlow/actions/runs/38882609920).
- Actual public package pages:
  [backend screenshot](screenshots/stockflow-ghcr-backend.png),
  [frontend screenshot](screenshots/stockflow-ghcr-frontend.png).
- [Pipeline evidence](../demo/PIPELINE_VIDEO_VERIFICATION.json) identifies the
  recorded source SHA. The walkthrough does not substitute a different run.

## M6 — Trivy

- [Strict scan script](../scripts/ci/scan-images.sh),
  [actual pipeline scan screenshot](screenshots/stockflow-trivy-ci.png), and
  [saved scan reports](security/).
- Trivy scans operating-system packages and installed application dependencies
  in both exact release images. The HIGH/CRITICAL gate passed for both images at
  the recorded run, so those image bytes could be published. This is a result
  for that vulnerability database and scan time, rather than a permanent claim
  of security or a statement that the separate Terraform findings disappeared.
- [Remediation and negative-gate proof](CI_SECURITY.md) explain the original
  Debian findings, Alpine base change, and verified rejection of a vulnerable image.

## M7 — Terraform and AWS

- [Terraform source](../terraform/) and
  [safe input example](../terraform/terraform.tfvars.example).
- [Original non-empty provisioning plan screenshot](screenshots/stockflow-terraform-initial-plan.png),
  [actual excerpt](evidence/terraform-initial-plan-excerpt.txt), and
  [source-log hash/provenance](evidence/terraform-initial-plan-provenance.json).
  The original plan had 59 additions. It is historical evidence, not a saved
  plan to apply again. The managed-project OIDC denial was later resolved using
  EKS Pod Identity, as documented in [the infrastructure review](INFRASTRUCTURE.md).
- [Live no-change plan](screenshots/stockflow-terraform-plan.png) verifies the
  already-deployed configuration without reprovisioning resources.
- Actual Sydney AWS Console captures:
  [EKS](screenshots/stockflow-aws-eks-console.png),
  [VPC](screenshots/stockflow-aws-vpc-console.png), and
  [two public/two private subnets](screenshots/stockflow-aws-vpc-subnets.png).
- [AWS verification](AWS_VERIFICATION.json): active cluster and managed node
  group, private worker, encrypted storage, and healthy load-balancer targets.
- **Actual destroy completion and its screenshot remain pending until cleanup
  after evaluation.** No simulated destroy result is submitted.

## M8 — Kubernetes and Helm

- [Namespace](../k8s/namespace.yaml), [Helm chart](../helm/stockflow/Chart.yaml),
  [values](../helm/stockflow/values.yaml), and [templates](../helm/stockflow/templates/).
- [Actual cloud Helm release screenshot](screenshots/stockflow-helm-list.png),
  [original Helm list output](CLOUD_HELM_LIST.txt), and
  [manual install/upgrade verification](CLOUD_HELM_VERIFICATION.json).
  The disposable `warehouse` release in `stockflow-smoke` was intentionally
  removed after proof was saved; the screenshot is labelled historical.
- Production uses ArgoCD to render/reconcile the same Helm chart. It does not
  create a Helm CLI release record in the production namespace.
- [Live pod execution](screenshots/stockflow-pods-terminal.png): two Ready
  backend replicas, two Ready frontend replicas, and PostgreSQL.
- [Live Services/Ingress execution](screenshots/stockflow-services-terminal.png):
  ClusterIP services and ALB routing. [Ingress template](../helm/stockflow/templates/ingress.yaml)
  routes `/api` to the backend and `/` to the frontend.

## M9 — Prometheus and Grafana

- [Monitoring configuration](../monitoring/),
  [actual curl output](screenshots/stockflow-curl-metrics.png),
  [live Targets showing the app UP](screenshots/stockflow-prometheus-targets-cloud.png),
  and [populated Grafana dashboard](screenshots/stockflow-grafana-walkthrough.png).
- [Cloud monitoring results](CLOUD_OBSERVABILITY_VERIFICATION.json) preserve the
  bounded load experiment and observed HPA scaling.

## M10 — Presentation and documentation

- [README](../README.md) includes setup, architecture, stack, CI, infrastructure,
  Kubernetes/Helm, monitoring, and known limitations.
- [11-slide PDF](../demo/slides.pdf) and
  [complete silent walkthrough](../demo/stockflow-walkthrough-silent.mp4).
  On-screen explanations and captions are used instead of narration, as requested.
- [Chapters](../demo/WALKTHROUGH.md) and
  [verification](../demo/WALKTHROUGH_VERIFICATION.json).
- Terraform and Kubernetes commands execute during the updated recording with
  stdout streamed from real processes. AWS Console views are actual captured
  project screens; the original provisioning plan and disposable Helm proof are
  explicitly labelled historical.

## External actions still required

1. Submit [this repository URL](https://github.com/Pyush269/StockOverFlow) through
   [the instructor's form](https://forms.gle/XWAP1vAumDJgAPM1A).
2. Agree the evaluation window, then perform the documented AWS cleanup and
   save the actual destroy result. AWS remains running and consumes credits.

The three reviewed Terraform configuration findings are documented in
[INFRASTRUCTURE.md](INFRASTRUCTURE.md). No credentials, local environment files,
binary plans, or Terraform state should be added to the repository or source ZIP.
