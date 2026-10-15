# Prompt 6: Helm and bootstrap verification

Prepared 15 October 2026. **Chart/bootstrap implementation and local runtime checks are complete. AWS remains off at the user's request.** EKS EBS/IRSA, live ALB routing, and real cloud Helm evidence are pending deployment.

## Implemented

The [StockFlow chart](../helm/stockflow) includes:

- A single persistent PostgreSQL StatefulSet, encrypted gp3 storage selection for EKS, retained PVCs, and an external credential Secret.
- A migration Job using the exact same SHA-tagged image as the API, bounded database waiting, and a PostgreSQL advisory lock to serialize migrations.
- Backend schema gating, startup/readiness/liveness probes, resource requests/limits, non-root identities, read-only root filesystems, dropped capabilities, RuntimeDefault seccomp, and no service-account token mount.
- Two frontend and two backend replicas; CPU-based backend HPA with min 2/max 3; PostgreSQL is not autoscaled.
- ClusterIP Services with named ports, ALB IP-target Ingress routes `/api` and `/`, and per-Service backend `/ready` and frontend `/health` target checks.
- A ServiceMonitor selecting the actual backend Service's `http` port and matching the bootstrap Prometheus selector.
- Configurable registry pull Secrets on all Pods, including migration and schema-wait containers.
- Production/local overlays, JSON schema guards, source-SHA consistency checks, arbitrary release/namespace support, and a separate credential-free [Helm CI workflow](../.github/workflows/helm.yml).

The chart defaults to the successful [71a3654 CI release](https://github.com/Pyush269/StockOverFlow/actions/runs/38739720946), whose published image manifests were verified. Both tags are the full source SHA. The application Docker images were not rebuilt for Helm support; bootstrap scripts run from a read-only ConfigMap.

## Startup and upgrades

For Helm, the migration is an ordinary Job whose name includes the release revision. Helm creates the database and Job together; the Job waits for PostgreSQL, and API init containers wait for the image's expected Alembic revision. Use **both** `--wait` and `--wait-for-jobs`. This avoids a pre-install hook depending on an uncreated database, and avoids a post-install hook waiting behind unready APIs. Helm upgrades replace the old revision's Job and run the new one.

For ArgoCD, the database, bootstrap ConfigMap, and ServiceAccount precede the migration. The migration is a **Sync** hook in wave 0, with `BeforeHookCreation,HookSucceeded`; workloads follow in wave 1, then Ingress/ServiceMonitor in wave 2. Do not convert it to a PreSync hook on initial installation. Database/pull Secrets must already exist. Prompt 7 will create and verify the ArgoCD Application; an installed ArgoCD controller alone is not a completed GitOps deployment.

The frontend uses the nameserver from its Kubernetes `/etc/resolv.conf`; it does not use Docker Compose's `127.0.0.11`. Its internal API upstream uses the release-specific backend Service. Direct ALB API routing and frontend port-forward proxying both use unchanged `/api` paths.

## Checks completed locally

The isolated cluster is `kind-stockflow-smoke`, using Kubernetes **1.36.4**, a separate `.logs/kind.kubeconfig`, one worker limited to **29 pods** and **two CPU cores**, plus a separate local control-plane container. Existing minikube and Compose application data were not changed.

- `helm lint --strict` and eight chart behavior tests passed: names/ports/routes, migration ordering, matching release images, external credentials, pod security/pull Secrets, HPA/scraping, retained storage/local settings, and rejected invalid values.
- The production manifests passed a Kubernetes server dry run, including the actual ServiceMonitor CRD. The upstream Gateway API and controller CRDs also passed server-side dry-run validation.
- A real Helm release named `warehouse` installed in `stockflow-smoke`; PostgreSQL PVC became Bound, migrations completed, and at least two frontend/backend replicas became Ready.
- HTTP checks passed through the frontend Nginx proxy: create product, receive 10, issue 3, reject an issue of 8, verify remaining quantity 7.
- A Helm upgrade reran a new migration Job and preserved inventory. The test was corrected to check the new Job identity; Helm removes the old revision's ordinary Job during upgrade.
- PostgreSQL pod replacement reused the same PVC and preserved quantity 7.
- Pinned Metrics Server, Prometheus/Grafana, and ArgoCD installed successfully. `kubectl top` and HPA CPU metrics work. Prometheus reports both StockFlow backend targets **UP**, with empty scrape errors.
- A conservative one-worker requests/pod-count projection passed. It reserves additional EKS system/controller overhead and allows an HPA replica, rollout surge, and migration. Actual EKS validation remains necessary.
- The revised one-worker Terraform configuration validates and all **11** mocked infrastructure tests pass. Its real saved plan is **59 additions, 0 changes, 0 destroys**; current base estimate is **$0.2890/hour**, or **$0.3335/hour** including illustrative later ALB/database storage, before variable usage and credits.

[Machine-readable verification](HELM_VERIFICATION.json) records the observed runtime and capacity checks. Detailed local reports remain under ignored `.logs/` paths. GitHub CI separately repeats lint, render behavior, and a real kind Helm install/upgrade/PVC recovery test without AWS credentials.

## Runbooks and limits

Use the [bootstrap runbook](../k8s/bootstrap/README.md) for pinned dependencies, local reproduction, guarded EKS bootstrap, and a disposable cloud smoke release. Use the [infrastructure review](INFRASTRUCTURE.md) for the exact saved plan, price assumptions, and three outstanding configuration scan findings. Those findings are not suppressed by the Helm work.

The chart does not commit database passwords. `scripts/create-k8s-secret.py` generates credentials in memory, sends them to Kubernetes through stdin, and preserves a matching existing Secret. It refuses one pointing at another release's database. Changing a database password requires coordinated database/Secret rotation; rerunning this helper does not perform rotation.

The local test does not validate IAM, EBS volume provisioning/attachment, AWS security-group reconciliation, internet ALB health, the real worker's allocatable resources, or recording/evaluation availability. The one-worker profile has no worker redundancy, and node updates can interrupt the entire demo. HPA scales Pods only; it does not add EC2 workers. Resource limits may need adjustment based on actual measurements.

Do not run the disposable Helm and final GitOps application concurrently on the one worker. Preserve needed PostgreSQL data before deliberately removing PVCs. Follow the grading cleanup timing and remove controller-managed ALBs before deleting the cluster.
