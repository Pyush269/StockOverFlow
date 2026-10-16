# Submission evidence

[Repository](https://github.com/Pyush269/StockOverFlow) |
[Full video](../demo/stockflow-walkthrough-silent.mp4) |
[11-slide PDF](../demo/slides.pdf)

Evidence mapped to the [instructor's grading rubric](https://github.com/Nency-Ravaliya/devsecops-python/blob/main/GRADING.md).
All recorded deployment results are from 16 October 2026.

## M1 - Application (10 points)

[FastAPI source](../backend/app/), [React source](../frontend/src/),
[Alembic migration](../backend/alembic/versions/0001_inventory.py), and
[Compose stack](../docker-compose.yml). The API includes GET, POST, PUT, and
DELETE product routes plus stock movements, dashboard, health, and readiness.

Evidence: [cloud website](screenshots/stockflow-cloud-overview.png),
[responsive mobile layout](screenshots/stockflow-cloud-mobile.png),
[cloud API/runtime checks](CLOUD_RUNTIME_VERIFICATION.json).

## M2 - Tests (10 points)

[49 backend tests](../backend/tests/), [pytest configuration](../backend/pytest.ini),
and [isolated fixtures](../backend/tests/conftest.py). Fixtures require
`stockflow_test`; [compose.ci.yml](../compose.ci.yml) provides temporary PostgreSQL.
Frontend unit tests and browser workflows are included in `frontend/tests` and `frontend/e2e`.

Evidence: [passing pytest screenshot](screenshots/stockflow-pytest-verbose.png),
[all verbose results](evidence/pytest-verbose.txt), and the
[successful CI run](https://github.com/Pyush269/StockOverFlow/actions/runs/38886848905).

## M3 - Git and GitHub (5 points)

Public [repository and history](https://github.com/Pyush269/StockOverFlow/commits/main/)
with meaningful commits and [.gitignore](../.gitignore).
[History screenshot with more than ten commits](screenshots/stockflow-git-history.png).
Repository submission through the instructor's form is a separate student action.

## M4 - Docker (10 points)

[Backend Dockerfile](../backend/Dockerfile),
[multi-stage frontend Dockerfile](../frontend/Dockerfile), and
[Compose stack](../docker-compose.yml). The application images use non-root users.

Evidence: [successful Compose startup](screenshots/stockflow-compose-startup.png)
and [application at localhost:3000](screenshots/stockflow-localhost-3000.png).

## M5 - CI/CD (15 points)

[GitHub Actions workflows](../.github/workflows/) test, build, scan, and publish.
Every main push runs application CI. Tests gate builds, and full commit SHA tags
identify both GHCR images. Publication uses the exact scanned image bytes.

Evidence: [successful run](https://github.com/Pyush269/StockOverFlow/actions/runs/38886848905),
[backend package](screenshots/stockflow-ghcr-backend.png),
[frontend package](screenshots/stockflow-ghcr-frontend.png), and the full video's
[recorded push/run](https://github.com/Pyush269/StockOverFlow/actions/runs/38867618119).

## M6 - Trivy (5 points)

[Scan script](../scripts/ci/scan-images.sh) and
[actual scan output](screenshots/stockflow-trivy-ci.png).

Trivy scanned the operating-system packages and installed application dependencies
in both release images. Both HIGH/CRITICAL gates passed for the recorded run, so
those image bytes could be published. The result applies to that scan time and
vulnerability database; it does not erase the separate Terraform configuration findings.

## M7 - Terraform (15 points)

[Terraform HCL and lockfile](../terraform/) and
[credential-free input example](../terraform/terraform.tfvars.example).

Evidence: [original non-empty plan](screenshots/stockflow-terraform-initial-plan.png),
[original excerpt](evidence/terraform-initial-plan-excerpt.txt),
[plan provenance](evidence/terraform-initial-plan-provenance.json),
[live no-change plan](screenshots/stockflow-terraform-plan.png),
[AWS EKS Console](screenshots/stockflow-aws-eks-console.png),
[VPC Console](screenshots/stockflow-aws-vpc-console.png),
[two public/two private subnets](screenshots/stockflow-aws-vpc-subnets.png), and
[AWS API verification](AWS_VERIFICATION.json).

The 59-addition plan is historical; the OIDC denial was later resolved with Pod
Identity. Actual destroy completion and its screenshot are to be collected during
[post-evaluation cleanup](INFRASTRUCTURE.md#cleanup-after-evaluation).

## M8 - Kubernetes and Helm (15 points)

[Namespace/bootstrap](../k8s/), [complete chart](../helm/stockflow/), and
[manual installation commands](../k8s/bootstrap/README.md).

Evidence: [Running pods](screenshots/stockflow-pods-terminal.png),
[ClusterIP Services and ALB Ingress](screenshots/stockflow-services-terminal.png),
[actual Helm list](screenshots/stockflow-helm-list.png),
[Helm runtime verification](CLOUD_HELM_VERIFICATION.json), and
[application through the ALB](screenshots/stockflow-cloud-overview.png).

The manual `warehouse` release in `stockflow-smoke` was removed after verification;
its screenshot is labelled historical. Production uses ArgoCD to render the same
Helm chart and has two Ready frontend and backend replicas.
[Synced/Healthy ArgoCD](screenshots/stockflow-argocd-walkthrough.png).

## M9 - Observability (10 points)

[Prometheus/Grafana values and dashboard](../monitoring/).
Evidence: [curl metrics](screenshots/stockflow-curl-metrics.png),
[Prometheus Targets UP](screenshots/stockflow-prometheus-targets-cloud.png),
[populated Grafana dashboard](screenshots/stockflow-grafana-walkthrough.png), and
[recorded observations](CLOUD_OBSERVABILITY_VERIFICATION.json).

## M10 - Presentation and documentation (5 points)

[Technical README](../README.md), [11-slide PDF](../demo/slides.pdf), and
[complete silent video](../demo/stockflow-walkthrough-silent.mp4).
[Chapters](../demo/WALKTHROUGH.md) and
[video verification](../demo/WALKTHROUGH_VERIFICATION.json).

The video covers slides, website/code, actual push and completed CI, Terraform,
AWS Console, ArgoCD, Kubernetes, Prometheus Targets, and Grafana. On-screen
explanations and captions replace narration. Terraform/Kubernetes commands
execute in the recording; historical evidence is labelled.

## Submission and evaluation

Submit the repository URL through [the instructor's form](https://forms.gle/XWAP1vAumDJgAPM1A).
After evaluation, perform AWS cleanup and save the real destroy screenshot.
AWS remains running and consumes credits until cleanup.
The [infrastructure notes](INFRASTRUCTURE.md) document the three reviewed
configuration findings. [Supplementary evidence provenance](evidence/SUPPLEMENTARY_VERIFICATION.json).
