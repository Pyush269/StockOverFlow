# Cluster bootstrap and Helm

Terraform owns AWS networking, EKS, IAM, and managed add-ons. This directory
contains Kubernetes-side bootstrap values. [versions.json](versions.json) pins
the controller charts and upstream Gateway API checksum.

| Release | Chart version | Purpose |
|---|---|---|
| aws-load-balancer-controller | 3.6.0 | Public ALB Ingress using EKS Pod Identity |
| metrics-server | 3.14.0 | Resource metrics and HPA |
| monitoring | kube-prometheus-stack 92.8.0 | Prometheus and Grafana |
| argocd | argo-cd 10.10.5 | GitOps reconciliation |

## Bootstrap EKS

Requirements: PowerShell, AWS CLI with profile `stockflow`, Terraform, Helm,
kubectl, Python 3.12, and `requirements-ops.txt`. Use Sydney (`ap-southeast-2`).
From the repository root after applying the reviewed Terraform plan:

```powershell
python scripts/configure-eks.py
$env:KUBECONFIG = Join-Path $PWD '.logs/eks.kubeconfig'
.\scripts\bootstrap-cluster.ps1 -Context stockflow-eks-sydney
```

The script verifies the Kubernetes endpoint against Terraform outputs. It applies
the encrypted gp3 StorageClass, checksum-verified Gateway API CRDs, controller
CRDs, and the pinned charts. The Load Balancer Controller receives explicit
cluster, VPC, and Region settings. Its Terraform-managed Pod Identity role is
scoped to the controller service account. Local Metrics Server TLS overrides
are used only by the isolated kind validation cluster.

## Manual Helm installation

The recorded manual release used `warehouse` in `stockflow-smoke`, separately
from the ArgoCD-managed production application. It was removed after the actual
install/upgrade/PVC proof was saved. Use the following only on a prepared cluster
with capacity for the disposable test release:

```powershell
$stockflowContext = 'stockflow-eks-sydney'
kubectl --context $stockflowContext create namespace stockflow-smoke
kubectl --context $stockflowContext label namespace stockflow-smoke pod-security.kubernetes.io/enforce=restricted pod-security.kubernetes.io/enforce-version=v1.36
python scripts/create-k8s-secret.py --context $stockflowContext --namespace stockflow-smoke --release warehouse --values helm/stockflow/values-prod.yaml --secret-name stockflow-smoke-db
helm upgrade --install warehouse helm/stockflow --kube-context $stockflowContext -n stockflow-smoke -f helm/stockflow/values-prod.yaml --set postgresql.existingSecret=stockflow-smoke-db --set ingress.enabled=false --set monitoring.serviceMonitor.enabled=false --wait --wait-for-jobs --timeout 10m
helm list --kube-context $stockflowContext -n stockflow-smoke
kubectl --context $stockflowContext -n stockflow-smoke get pods,svc,pvc,hpa,jobs
```

The smoke overlay disables Ingress to avoid a second ALB. The runtime helper
`scripts/helm-smoke.py` checks migrations, stock rules, two Ready replicas of
each application tier, and retained data after PostgreSQL replacement. It is
restricted to namespaces ending in `-smoke`.

[Actual Helm result](../../docs/CLOUD_HELM_VERIFICATION.json) and
[Helm list output](../../docs/CLOUD_HELM_LIST.txt).
Do not install another Helm release over the production resources.
For the production Application, follow [the GitOps steps](../../argocd/README.md).

The Helm CI workflow uses `k8s/local-kind.yaml`, local chart values, and the same
chart tests to verify installation without creating AWS resources.
