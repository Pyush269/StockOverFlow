# Monitoring, load, and recovery evidence

The local observations below were verified on 15 October 2026 using the isolated two-core kind worker. Later EKS checks passed on 16 October, including **4,601 public GET requests with no failures**, six populated queries, stable Grafana, and observed **HPA 2 -> 3 -> 2**. See [the cloud report](CLOUD_OBSERVABILITY_VERIFICATION.json). Keep the local and cloud measurements separate.

## Recorded results

The committed [dashboard](../monitoring/stockflow.json) is provisioned from Git.
Its six panels show API request rate, histogram-based p95 latency, 5xx rate,
backend CPU/memory, and Ready backend replicas. All six queries returned finite
live values through Prometheus, and the Grafana UI rendered without empty panels.

The final bounded experiment sent **8,780 GET requests in 120.02 seconds**, with
**0 failures**, using 12 workers and a total target ceiling of 80 requests/second.
Measured throughput was **73.16 requests/second**; client median latency was
**31 ms** and p95 was **203 ms**. This uses a small demo database and a localhost
port-forward; it does not predict production capacity or internet latency.

The HPA started at two Ready backend replicas, scaled to **three Ready replicas**
under real CPU demand, and returned to **two** after traffic stopped and the
configured stabilization window elapsed. ArgoCD did not overwrite HPA's replica
count. Prometheus observed three backend scrape targets UP during the load.
Its target count follows the current replica count.

Evidence: [machine-readable report](OBSERVABILITY_VERIFICATION.json),
[actual Grafana screenshot](screenshots/stockflow-grafana-local.png), and the
[monitoring runbook](../monitoring/README.md). The JSON includes timestamp-offset
HPA samples, query expressions/results, load status counts, and container state.

## Longer-running issue found and corrected

The initial Helm installation became Ready, but its Grafana dashboard and
datasource sidecars later exceeded their **64 MiB** limits and were OOMKilled.
The canonical [monitoring values](../monitoring/values.yaml) now give each sidecar
a **96 MiB request / 256 MiB limit**. The replacement Grafana pod stayed 3/3 Ready
with **zero restarts** throughout the successful experiment. The main Grafana
container keeps a 384 MiB limit. The earlier short readiness result alone was
insufficient evidence of sustained health.

The [one-worker planning calculation](KUBERNETES_CAPACITY.json) was repeated with
the higher requests: projected 1,755m CPU, 3,418 MiB memory, and 28 Pods against
planning budgets of 1,900m CPU, 6,800 MiB, and 29 Pods.
Actual EKS allocatable resources and add-on requests remain a deployment check;
CPU/pod headroom is limited. The script can conservatively double-reserve an
HPA/migration slot if run while those extra Pods already exist. Record a steady
two-replica sample for the baseline, and inspect real Pending/OOM events.

## Reproduction

Use the [bootstrap](../k8s/bootstrap/README.md) and [GitOps](../argocd/README.md)
runbooks first. The local experiment creates only bounded read traffic and owns
its temporary localhost port-forwards:

```powershell
. ..\Enter-Project.ps1
$env:KUBECONFIG = Join-Path $PWD '.logs/kind.kubeconfig'
python scripts/verify-monitoring.py --context kind-stockflow-smoke
```

Node 22, the frontend's locked Playwright dependency, and its project Chromium
installation are needed for screenshot capture. The helper reuses the full
Chromium channel installed with `--no-shell`. Generated Grafana credentials stay
in memory and travel to the isolated browser through stdin.

Cloud mode is restricted to the applied Sydney endpoint and `stockflow` namespace. Run `python scripts/verify-monitoring.py --cloud --context stockflow-eks-sydney --namespace stockflow --duration 120 --concurrency 32 --rps 200` with the project EKS kubeconfig. The configured RPS is a ceiling; the measured final rate was 38.09 requests/second from this client. EKS uses verified kubelet TLS, without the local self-signed exception.

Backend Pod recovery and inventory across the GitOps release/rollback are
recorded separately in [the GitOps evidence](GITOPS_VERIFICATION.json).

## Cloud verification, 16 October 2026

The cloud experiment passed with six populated dashboard queries, healthy backend scrape targets, stable Grafana containers, and observed HPA scaling. See [the actual cloud report](CLOUD_OBSERVABILITY_VERIFICATION.json) and [cloud Grafana screenshot](screenshots/stockflow-grafana-cloud.png). Run `python scripts/verify-monitoring.py --cloud --context stockflow-eks-sydney --namespace stockflow` with `.logs/eks.kubeconfig`. EKS uses verified kubelet TLS; the local-only exception was not carried into the cloud.
