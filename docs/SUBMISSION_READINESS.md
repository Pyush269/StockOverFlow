# Submission readiness

Prepared 16 October 2026. The presenter requested a silent video; on-screen
explanations and captions replace narration.

| Required video section | Submitted evidence |
|---|---|
| Slides first | All 11 pages of [slides.pdf](../demo/slides.pdf) open the video |
| Codebase | Folder responsibilities, inventory transaction source, test output, Dockerfile |
| Push and end-to-end CI | Actual [successful push run](https://github.com/Pyush269/StockOverFlow/actions/runs/38867618119), including tests, strict scans, and GHCR publication |
| Terraform | Fresh read-only plan: no changes after the existing deployment |
| AWS Console | Actual [EKS](screenshots/stockflow-aws-eks-console.png) and [VPC](screenshots/stockflow-aws-vpc-console.png) captures in Sydney |
| ArgoCD | Live Synced/Healthy application and explanation of Git image promotion |
| Kubernetes | Actual healthy pod, Service, and Ingress command output |
| Prometheus | Live [Targets page](screenshots/stockflow-prometheus-targets-cloud.png): two backend targets UP |
| Grafana | Live [dashboard](screenshots/stockflow-grafana-walkthrough.png) with application metrics |

Primary artifact: [complete silent walkthrough](../demo/stockflow-walkthrough-silent.mp4).
[Chapters and sources](../demo/WALKTHROUGH.md), [machine-readable verification](../demo/WALKTHROUGH_VERIFICATION.json).

Application CI now runs on every push to `main`, including documentation-only
pushes. The [trigger correction passed](https://github.com/Pyush269/StockOverFlow/actions/runs/38872525116).
The video preserves the actual earlier recorded push, rather than presenting a
different successful run as that recording.

## Remaining evaluation actions

- Submit the repository URL using the instructor's submission form. Submission
  has not been claimed or performed automatically.
- Confirm the evaluation window. AWS is running and consumes credits, at the
  reviewed estimate of about $0.33/hour plus usage.
- After evaluation, back up needed inventory, remove controller-created ALB and
  workloads, review/run Terraform destroy, verify resource removal, and save
  real destroy evidence. Do not delete Terraform state beforehand.

Three reviewed Terraform configuration scan findings remain documented in
[INFRASTRUCTURE.md](INFRASTRUCTURE.md). The successful image vulnerability gates
are separate; their result does not erase these infrastructure findings.
