# Cluster bootstrap

The AWS deployment is currently **off by user choice**. Prompt 6 was exercised on an isolated local Kubernetes cluster; it does not prove that EBS/IRSA or an ALB works on EKS. Read [the infrastructure review](../../docs/INFRASTRUCTURE.md) before approving the real deployment.

## Pinned dependencies

[versions.json](versions.json) records the checked chart/application versions, application image release, local node image, and Gateway API checksum. IAM and EKS managed add-ons belong to Terraform. Helm installs only the Kubernetes-side dependencies below.

| Release | Chart version | Purpose |
|---|---|---|
| aws-load-balancer-controller | 3.6.0 | ALB Ingress; exact IRSA service account from Terraform |
| metrics-server | 3.14.0 | Resource Metrics API for `kubectl top` and HPA |
| monitoring | kube-prometheus-stack 92.8.0 | Prometheus operator/CRDs, Prometheus, Grafana, node and workload metrics |
| argocd | argo-cd 10.10.5 | GitOps controller/UI; Application configuration follows in Prompt 7 |

The one-worker profile uses single-replica controllers, disables unused Dex/notifications/Alertmanager, and sets resource requests and limits. The canonical monitoring chart values are in [monitoring/values.yaml](../../monitoring/values.yaml). Prometheus retains six hours of data in ephemeral storage. The StockFlow dashboard is provisioned from Git by `kubectl apply -k monitoring`; UI-only edits/history are ephemeral. This profile is for a short demo, with no worker redundancy. The PostgreSQL PVC is persistent.

## Local verification without AWS

Docker Desktop with Linux containers, Helm 3.22, kubectl, Python 3.12/PyYAML 6.0.3, and kind 0.33 are needed. Existing project tools can be exposed with `. ..\Enter-Project.ps1`. The local test has its own kubeconfig and does not change the existing minikube configuration.

```powershell
# From stockflow/. Use the verified kind binary on PATH or .logs/tools/kind.exe.
$env:KUBECONFIG = Join-Path $PWD '.logs/kind.kubeconfig'
kind create cluster --name stockflow-smoke --config k8s/local-kind.yaml --kubeconfig $env:KUBECONFIG --image 'kindest/node:v1.36.4@sha256:099e049362a1526b2db71494e1947aae99bd16290d7c895f2b7ea312e3cbfaed' --wait 120s
docker update --cpus 2 stockflow-smoke-worker
.\scripts\bootstrap-cluster.ps1 -Context kind-stockflow-smoke -Local
kubectl --context kind-stockflow-smoke create namespace stockflow-smoke
kubectl --context kind-stockflow-smoke label namespace stockflow-smoke pod-security.kubernetes.io/enforce=restricted pod-security.kubernetes.io/enforce-version=v1.36
python scripts/create-k8s-secret.py --context kind-stockflow-smoke --namespace stockflow-smoke --release warehouse --values helm/stockflow/values-local.yaml --secret-name stockflow-smoke-db
helm upgrade --install warehouse helm/stockflow --kube-context kind-stockflow-smoke -n stockflow-smoke -f helm/stockflow/values-local.yaml --set postgresql.existingSecret=stockflow-smoke-db --set monitoring.serviceMonitor.enabled=true --wait --wait-for-jobs --timeout 10m
python scripts/helm-smoke.py --context kind-stockflow-smoke --values helm/stockflow/values-local.yaml --monitoring
```

The local-only Metrics Server override permits the kind kubelet's self-signed serving certificates. It is not used by the EKS bootstrap. The cloud configuration explicitly uses the cluster CA for AL2023 kubelet serving certificates. Check the certificate chain and API connectivity if cloud metrics fail; do not silently carry the local TLS exception into EKS.

## Cloud prerequisites, after deployment approval

Apply the newly reviewed **one-worker** Terraform plan in Sydney, then configure kubeconfig with profile `stockflow` and confirm the correct EKS context. Credentials and Terraform state stay outside Git. Read the cloud identity and endpoint from the applied Terraform outputs; the bootstrap script refuses a mismatched Kubernetes endpoint or Region.

```powershell
# From stockflow/, only after the Terraform plan has been approved and applied.
$env:AWS_PROFILE = 'stockflow'
$env:AWS_REGION = 'ap-southeast-2'
aws eks update-kubeconfig --profile stockflow --region ap-southeast-2 --name stockflow-eks
$stockflowContext = kubectl config current-context
kubectl --context $stockflowContext get nodes -o wide
.\scripts\bootstrap-cluster.ps1 -Context $stockflowContext
```

Bootstrap applies the encrypted `gp3` StorageClass, upstream Gateway API **v1.6.0** definitions, and the AWS-specific CRDs supplied by the pinned controller chart. These are different sets of CRDs; AWS Gateway configuration CRDs alone do not provide the upstream Gateway APIs. The upstream download is checksum verified. The controller receives `clusterName`, `region`, `vpcId`, and its IRSA role ARN from Terraform outputs; IMDS hop limit remains 1. Shield/WAF integrations are disabled for this demo.

The bootstrap does not create application database credentials or deploy the GitOps Application. It creates no extra IAM role through eksctl. On later chart upgrades, review release notes and apply compatible CRD changes explicitly; Helm does not upgrade CRDs automatically. [AWS controller installation](https://docs.aws.amazon.com/eks/latest/userguide/lbc-helm.html), [controller 3.6.0 release](https://github.com/kubernetes-sigs/aws-load-balancer-controller/releases/tag/v3.6.0), [Helm CRD behavior](https://helm.sh/docs/chart_best_practices/custom_resource_definitions/).

## Real cloud Helm smoke release

Use a disposable namespace and release so Helm ownership stays separate from the future ArgoCD-managed `stockflow` application. Disable Ingress for this smoke release to avoid a second ALB; disable ServiceMonitor unless you intentionally enable the smoke scrape target. Create the Secret before installing.

```powershell
kubectl --context $stockflowContext create namespace stockflow-smoke
kubectl --context $stockflowContext label namespace stockflow-smoke pod-security.kubernetes.io/enforce=restricted pod-security.kubernetes.io/enforce-version=v1.36
python scripts/create-k8s-secret.py --context $stockflowContext --namespace stockflow-smoke --release warehouse --values helm/stockflow/values-prod.yaml --secret-name stockflow-smoke-db
helm upgrade --install warehouse helm/stockflow --kube-context $stockflowContext -n stockflow-smoke -f helm/stockflow/values-prod.yaml --set postgresql.existingSecret=stockflow-smoke-db --set ingress.enabled=false --set monitoring.serviceMonitor.enabled=false --wait --wait-for-jobs --timeout 10m
python scripts/helm-smoke.py --context $stockflowContext --values helm/stockflow/values-prod.yaml
helm list --kube-context $stockflowContext -n stockflow-smoke
kubectl --context $stockflowContext get pods,svc,pvc,hpa,jobs -n stockflow-smoke
```

The runtime verifier is restricted to namespaces ending in `-smoke`. It creates demo inventory, tests overselling, upgrades the release, and replaces its PostgreSQL pod. It always disables Ingress during upgrades, even with production values. It never deletes a PVC or namespace. Save screenshots of `helm list`, Ready replicas, migration completion, Bound gp3 PVC, and persistence after pod replacement. These EKS checks are still pending.

After collecting evidence, uninstall only this disposable release. Confirm its data is disposable before deleting its retained PVC and Secret. Remove it **before** the real GitOps app so the one worker does not host both application copies simultaneously. The script does not clean up data automatically.

## Capacity and access

The `m7i-flex.large` API reports 3 ENIs and 10 IPv4 addresses per interface, giving the standard CNI limit of **29 pods**. Local tests enforce this same worker pod limit and limit its Docker CPU quota to two cores. Local storage/networking differ from EKS.

The local full-stack check reserves 6 additional pods, 500m CPU, and 1 GiB memory for the missing EKS system components and controller. It projects another backend replica (HPA max 3), frontend/backend rollout surge, and a migration Job. See [the recorded capacity result](../../docs/HELM_VERIFICATION.json). Treat the requests/pod-count calculation as a planning bound, not a peak-memory or performance guarantee. After real deployment, check actual node allocatable resources, default add-on requests, EBS topology, and all Pending/OOM/eviction events. Increase to two workers through Terraform if checks fail.

```powershell
kubectl --context $stockflowContext get nodes -o wide
kubectl --context $stockflowContext top nodes
kubectl --context $stockflowContext top pods -A
kubectl --context $stockflowContext get events -A --sort-by=.lastTimestamp
```

Grafana, Prometheus, and ArgoCD use ClusterIP Services. Use localhost port-forwards; no additional public load balancers are needed:

```powershell
kubectl --context $stockflowContext -n argocd port-forward svc/argocd-server 8443:443
# A separate terminal: open https://localhost:8443 (local self-signed certificate).
kubectl --context $stockflowContext -n monitoring port-forward svc/monitoring-grafana 3002:80
kubectl --context $stockflowContext -n monitoring port-forward svc/monitoring-kube-prometheus-prometheus 9090:9090
```

Retrieve each UI's generated admin password directly in your terminal when needed; do not save it to screenshots, Git, or reports. Add the real ArgoCD Application and database Secret in Prompt 7. The app's future ALB Ingress uses HTTP and demo inventory; use a domain/ACM certificate and suitable authentication before handling sensitive data.
