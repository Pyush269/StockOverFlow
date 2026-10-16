# Verified AWS deployment

Verified 16 October 2026 in **Sydney (`ap-southeast-2`)**, using profile `stockflow`.

Public application: [http://k8s-stockflo-stockflo-96a126ddd5-1324338338.ap-southeast-2.elb.amazonaws.com](http://k8s-stockflo-stockflo-96a126ddd5-1324338338.ap-southeast-2.elb.amazonaws.com)

The URL is served by AWS and can be opened from another computer while the resources remain running. Local Docker is not required to open it. This short demo uses HTTP and demo inventory.

| Check | Actual result | Evidence |
|---|---|---|
| Infrastructure | EKS ACTIVE; one Ready private worker; no public worker IP; encrypted gp3 root; five ACTIVE add-ons | [AWS checks](AWS_VERIFICATION.json) |
| Manual Helm | Install, upgrade/migration, stock validation, PostgreSQL replacement, same PVC and quantity 7; two Ready frontend/backend replicas | [Runtime](CLOUD_HELM_VERIFICATION.json), [helm list](CLOUD_HELM_LIST.txt), [resources](CLOUD_HELM_RESOURCES.txt) |
| GitOps | Baseline, image promotion, Git revert rollback, backend replacement, database replacement; quantity 7 retained on the same PVC | [Cloud stages](CLOUD_RUNTIME_VERIFICATION.json) |
| Storage and routing | Encrypted 10 GiB gp3 attached to worker; public ALB active with healthy frontend/API targets | [AWS API checks](AWS_VERIFICATION.json) |
| Monitoring | Six finite live dashboard queries, 3 UP backend scrape targets, stable Grafana, observed HPA 2 -> 3 -> 2 | [Cloud monitoring](CLOUD_OBSERVABILITY_VERIFICATION.json) |
| Bounded traffic | 4,601 read requests, 0 failures | Same cloud monitoring report |
| Capacity | Full stack plus HPA/rollout/migration projection fits 1,930m CPU and 29 pod slots; limited pod headroom | [Capacity](CLOUD_KUBERNETES_CAPACITY.json) |

The separate disposable Helm namespace and its test PVC were intentionally removed after proof was saved, before the final application was installed. The production inventory/PVC remain.

At the final snapshot, one old backend target was deregistering after HPA scale-down; two active backend and two frontend targets were healthy. AWS describes this temporary state as [connection draining](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/target-group-health-checks.html).

## Deployment corrections

The managed AWS project SCP denied IAM OIDC provider creation. Terraform was changed to supported **EKS Pod Identity**, retaining exact cluster/namespace/service-account trust and separate CNI/EBS/controller permissions. Organization policies and the free plan were not changed. The storage policy ARN was corrected to the root-path `AmazonEBSCSIDriverPolicyV2`, with an IAM lookup during real planning. The provider lock was refreshed after removing TLS. The corrected Terraform workflow passed.

The refreshed configuration scan still exits 1 with **AWS-0040, AWS-0041, AWS-0104 (three CRITICAL findings)**. They are documented in [INFRASTRUCTURE.md](INFRASTRUCTURE.md), and not suppressed. This is separate from the strict image HIGH/CRITICAL gate.

## Recheck the running demo

```powershell
. ..\Enter-Project.ps1
python scripts/configure-eks.py
$env:KUBECONFIG = Join-Path $PWD '.logs/eks.kubeconfig'
python scripts/verify-aws.py
kubectl --context stockflow-eks-sydney -n argocd get application stockflow
kubectl --context stockflow-eks-sydney -n stockflow get pods,pvc,ingress,hpa
```

For the bounded monitoring experiment, run `python scripts/verify-monitoring.py --cloud --context stockflow-eks-sydney --namespace stockflow`. It creates only read traffic and temporary localhost admin forwards. The recovery/storage stages intentionally replace the corresponding demo Pod; run them only when a brief demo interruption is acceptable.

Latest application, Helm, and Terraform checks passed: [CI evidence](CLOUD_CI_VERIFICATION.json). The low-load public check also passed (1,754 requests with no failures); the final higher-concurrency check produced the scaling evidence.

## Cost and remaining submission work

The reviewed estimate remains **$0.2890/hour infrastructure**, or **$0.3335/hour full demo**, before variable usage and credits (about **$8/day**). AWS keeps running when this laptop or Docker stops. No scheduled shutdown was configured. Keep resources for the agreed evaluation window, then back up needed inventory and perform the documented cleanup. Destroying the ALB/EKS removes the public URL. Never delete Terraform state before cleanup verification.

The mandatory personal walkthrough video and AWS Console portion still need recording using [the recording guide](../demo/RECORDING.md). A narrated video has not been generated or uploaded. Post-evaluation destroy evidence must be collected when cleanup actually runs.
