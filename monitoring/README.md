# StockFlow monitoring

The canonical Prometheus/Grafana chart settings are [values.yaml](values.yaml).
Pinned versions remain in `k8s/bootstrap/versions.json`. The bootstrap script
installs `kube-prometheus-stack`, then applies this directory's Kustomization to
provision [stockflow.json](stockflow.json) as a Grafana dashboard ConfigMap.

```powershell
# Explicit local context; for EKS, use its verified context only after approval.
$env:KUBECONFIG = Join-Path $PWD '.logs/kind.kubeconfig'
kubectl --context kind-stockflow-smoke apply -k monitoring
kubectl --context kind-stockflow-smoke -n monitoring port-forward svc/monitoring-grafana 3002:80
```

Open http://localhost:3002, sign in with the generated Grafana admin credentials,
then open dashboard UID `stockflow-overview`. Select the app namespace. The
Prometheus datasource UID is `prometheus`; its URL points at the in-cluster
Prometheus Service. Credential values stay outside Git and evidence files.

## Dashboard queries

Six panels use metrics confirmed from the deployed instrumentation:

| Panel | Metric |
|---|---|
| API request rate | `http_requests_total`, `/api/` handlers |
| API p95 latency | `http_request_duration_seconds_bucket`, histogram quantile |
| API 5xx rate | `http_requests_total` grouped 5xx statuses; zero only when API series exist |
| Backend CPU | `container_cpu_usage_seconds_total` from kubelet/cAdvisor |
| Backend memory | `container_memory_working_set_bytes` from kubelet/cAdvisor |
| Backend Ready replicas | `kube_deployment_status_replicas_available` |

No-traffic latency can be absent/NaN. Generate real API traffic before presenting
the dashboard. A zero error rate is expected when every request succeeds.

## Bounded load and observations

In a terminal with a frontend localhost port-forward (3001 -> 80):

```powershell
.\scripts\load-test.ps1 -BaseUrl http://127.0.0.1:3001 -DurationSeconds 120 -Concurrency 12 -RequestsPerSecond 80
# In another terminal, observe metrics and current/desired replicas:
kubectl --context kind-stockflow-smoke -n stockflow-gitops-smoke get hpa -w
kubectl --context kind-stockflow-smoke -n stockflow-gitops-smoke top pods
```

Only GET `/api/products?limit=20` and GET `/api/dashboard` receive load. Duration,
worker count, and aggregate RPS are capped; transport/non-200 failures are visible
and fail the run. The verifier records observed replicas instead of assuming
scaling happened. Its full experiment is restricted to the local disposable
cluster:

```powershell
python scripts/verify-monitoring.py --context kind-stockflow-smoke
```

It owns and closes its localhost port-forwards, uses generated Grafana credentials
in memory, authenticates the real dashboard in isolated Chromium, and records
all six query results, target health, bounded traffic, HPA samples, and Grafana
container stability. It does not write inventory or start AWS resources.

## Memory correction and limits

The earlier 64 MiB sidecar limit caused Grafana dashboard/datasource sidecars to
be OOMKilled during a longer observation. Each now requests 96 MiB and can use
256 MiB; the main Grafana container retains its 384 MiB limit. The replacement
pod was checked through the full traffic experiment. Capacity must be rechecked
on the real EKS worker; local scheduling is not proof of cloud capacity.

Prometheus retains six hours in ephemeral storage. Grafana's provisioned JSON
survives recreation from Git, while UI-only dashboard edits and monitoring history
may be lost. PostgreSQL application data uses a separate persistent PVC. This
demo does not configure alert routing, HA monitoring, or public Grafana access.
