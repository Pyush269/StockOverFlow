# Deployment and evaluation checklist

AWS deployment was authorized on 16 October 2026 after refreshing the plan and
costs. Terraform provisioning is in progress; no verified public URL exists yet. Local Docker/Compose remains
usable on another computer with the documented prerequisites and a fresh `.env`.

## Before starting the paid-resource clock

- Confirm the recording/evaluation window and keep time for troubleshooting.
- Use profile `stockflow` in `ap-southeast-2`; reauthenticate if expired.
- Recheck the free-plan status, remaining credits, regional quota, and running
  resources. Do not upgrade to a paid plan silently.
- Refresh the current public operator IPv4 `/32` allowlist and Terraform plan.
  Review actual resource changes, current prices, and the three documented
  configuration scan findings in `INFRASTRUCTURE.md`.
- The current estimate is about $0.29/hour for infrastructure or $0.33/hour for
  the full demo, plus variable usage. A proposed $10 recording allowance is not
  an enforced spending cap. Stopping local Docker does not stop AWS usage.
- Review the exact plan before applying. Do not reuse an outdated plan merely
  because a previous hash is documented.

## Provisioning and cloud checks

1. Apply the newly reviewed Terraform plan and save actual completion evidence.
2. Verify EKS, node group, add-ons, operator access, and private worker placement.
3. Run `scripts/bootstrap-cluster.ps1` against the verified EKS context. It reads
   applied outputs, checks the Region/endpoint, and installs pinned dependencies.
4. Verify the worker's real allocatable CPU/memory/pod count and component
   requests. The one-worker projection has little CPU/pod headroom. Increase to
   two workers through a reviewed Terraform change if scheduling checks fail.
5. Confirm EBS CSI role permissions and an actual Bound encrypted gp3 PVC.
6. Deploy and exercise the disposable manual Helm release, save `helm list`/
   replica/storage evidence, then uninstall its workloads before GitOps.
7. Prepare the final `stockflow` namespace and generated database Secret. Install
   the restricted AppProject and production Application, then perform manual
   sync. Confirm migration success and two Ready frontend/backend replicas.
8. Verify Load Balancer Controller Pod Identity, ALB reconciliation, target health, and
   both frontend and API routes through the public hostname. No purchased domain
   is needed. Use only demo data with the current HTTP/no-auth app.
9. Enable automated sync after health checks. Verify live images match Git;
   demonstrate a compatible promotion/rollback and retained inventory.
10. Verify cloud Metrics Server TLS, HPA metrics, Prometheus targets, Grafana
    panels, bounded read traffic, and replacement of a backend Pod.

Use `argocd/README.md`, `k8s/bootstrap/README.md`, and `monitoring/README.md` for
commands. Explicit kube contexts prevent accidental use of the local cluster.

## Submission

- Capture actual screenshots as each cloud check passes.
- Update `demo/slides.pdf` from the recorded evidence; keep its AWS status honest.
- Follow `demo/RECORDING.md` to record the mandatory walkthrough.
- Upload the video under `demo/` or as a repository release asset; link it clearly.
- Verify repository/video access from another browser/device.
- Confirm the stated deadline with the instructor: the source document pairs
  Sunday with 19 October 2026, which is Monday.

The current rubric accepts a PDF slide deck, but a missing walkthrough video
loses the presentation module. Local results do not replace the real AWS
provisioning and public Ingress evidence. Sources:
[grading](https://github.com/Nency-Ravaliya/devsecops-python/blob/main/GRADING.md),
[submission](https://github.com/Nency-Ravaliya/devsecops-python/blob/main/SUBMISSION.md).

## After evaluation

Keep resources available until evaluation unless the instructor agrees otherwise.
Back up any required database data before deleting PVCs. Stop ArgoCD reconciliation,
remove the Ingress while its controller is running, confirm ALB/target group
deletion, remove workloads and disposable PVCs deliberately, then plan/review/run
Terraform destroy from the original state. Verify EKS, EC2, NAT/EIP, ALB, EBS,
snapshots, and log groups. Save actual destroy output; never mark it complete
before it runs. See `INFRASTRUCTURE.md` for the full cleanup sequence.
