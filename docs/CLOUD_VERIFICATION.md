# Verified AWS deployment

Verified on 16 October 2026 in Sydney (`ap-southeast-2`), profile `stockflow`.

[Public StockFlow application](http://k8s-stockflo-stockflo-96a126ddd5-1324338338.ap-southeast-2.elb.amazonaws.com)

| Component | Recorded result | Evidence |
|---|---|---|
| AWS | ACTIVE EKS, one Ready private worker, encrypted gp3 storage, active add-ons, healthy ALB targets | [AWS verification](AWS_VERIFICATION.json) |
| Helm | Install and upgrade, two migration runs, two Ready replicas per application tier, same PVC and quantity 7 after database pod replacement | [Helm verification](CLOUD_HELM_VERIFICATION.json), [Helm list](CLOUD_HELM_LIST.txt) |
| GitOps | Synced/Healthy baseline, promotion and Git revert rollback; inventory retained after backend/database pod replacement | [Runtime stages](CLOUD_RUNTIME_VERIFICATION.json) |
| Monitoring | Six finite dashboard queries, healthy targets, stable Grafana, observed HPA scaling from 2 to 3 and back | [Observability verification](CLOUD_OBSERVABILITY_VERIFICATION.json) |
| Application and pipeline | Live dashboard/catalog, completed push-triggered CI, real Terraform and Kubernetes command execution | [Full video verification](../demo/WALKTHROUGH_VERIFICATION.json) |

The cloud monitoring experiment recorded 4,601 successful read requests and
three backend targets during scaling. The final walkthrough captured the normal
two-replica deployment with both Prometheus targets UP.
The manual `warehouse` release was disposable and was removed after proof was
saved. The production ArgoCD application and its inventory PVC remain deployed.

The original managed-project OIDC denial was resolved using supported EKS Pod
Identity. The three remaining Terraform configuration scan findings and current
operating limits are documented in [INFRASTRUCTURE.md](INFRASTRUCTURE.md).

## Recheck

```powershell
python scripts/configure-eks.py
$env:KUBECONFIG = Join-Path $PWD '.logs/eks.kubeconfig'
python scripts/verify-aws.py
kubectl --context stockflow-eks-sydney -n argocd get application stockflow
kubectl --context stockflow-eks-sydney -n stockflow get pods,pvc,ingress,hpa
```

The public URL works from other computers while AWS is running. Laptop shutdown
or stopping local Docker does not stop AWS. After evaluation, collect the actual
Terraform destroy evidence using [the cleanup procedure](INFRASTRUCTURE.md#cleanup-after-evaluation).
