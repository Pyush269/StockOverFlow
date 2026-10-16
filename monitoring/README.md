# Prometheus and Grafana

[values.yaml](values.yaml) configures `kube-prometheus-stack`.
[kustomization.yaml](kustomization.yaml) provisions the Grafana dashboard from
[stockflow.json](stockflow.json). The application chart creates a ServiceMonitor.
Pinned chart versions are in [versions.json](../k8s/bootstrap/versions.json).

After cluster bootstrap, from the repository root:

```powershell
kubectl --context stockflow-eks-sydney apply -k monitoring
# Run these port-forwards in separate terminals:
kubectl --context stockflow-eks-sydney -n monitoring port-forward svc/monitoring-kube-prometheus-prometheus 9090:9090
kubectl --context stockflow-eks-sydney -n monitoring port-forward svc/monitoring-grafana 3002:80
kubectl --context stockflow-eks-sydney -n stockflow port-forward svc/stockflow-stockflow-backend 8001:8000
```

Open [Prometheus Targets](http://localhost:9090/targets) and
[Grafana](http://localhost:3002/d/stockflow-overview). Sign in to Grafana with its
generated admin credentials, select namespace `stockflow`, and use datasource
`prometheus`. Credentials stay outside screenshots and Git.

```powershell
curl.exe --fail http://localhost:8001/metrics
```

| Panel | Metric |
|---|---|
| Request rate | `http_requests_total` for `/api/` handlers |
| p95 latency | `http_request_duration_seconds_bucket` |
| 5xx rate | `http_requests_total` with 5xx status labels |
| CPU | `container_cpu_usage_seconds_total` |
| Memory | `container_memory_working_set_bytes` |
| Ready replicas | `kube_deployment_status_replicas_available` |

Generate actual API traffic before checking latency; no-traffic latency can be
absent. A zero error rate is expected for successful requests.
[Recorded cloud observations](../docs/CLOUD_OBSERVABILITY_VERIFICATION.json)
include finite queries, target health, and observed HPA scaling. The bounded
verification helper is `scripts/verify-monitoring.py --cloud --context
stockflow-eks-sydney --namespace stockflow`.

Prometheus retains six hours in ephemeral storage. Git-provisioned dashboards
survive recreation; historical metrics and UI-only edits may be lost. The demo
has no alert routing or redundant monitoring replicas.
