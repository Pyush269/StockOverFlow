# StockFlow infrastructure review

Prepared 15 October 2026; revised for the one-worker demo after Prompt 6 local capacity checks. **Prompt 5 is implemented and planned; deployment is pending review.** No Terraform apply has run and no StockFlow AWS infrastructure has been created. The existing default VPC remains outside this Terraform configuration.

## Actual plan and verification

The real Sydney plan is **59 to add, 0 to change, 0 to destroy**. These are Terraform-managed resource entries, not 59 virtual machines; the node group will create one EC2 worker and its root volume through AWS. The plan also defers the OIDC TLS certificate lookup until the cluster exists.

Local files, deliberately excluded from Git:

- Saved binary plan: `terraform/stockflow.tfplan`.
- Readable plan: `.logs/terraform-plan.txt`; complete JSON: `.logs/terraform-plan.json`.
- Actual project, operator role, and current public IPv4/32: `terraform/terraform.tfvars`.
- Test output: `.logs/terraform-tests.txt`.
- Configuration scan: `.logs/terraform-security.json` and `.logs/terraform-security.log`.
- Price lookup evidence: `.logs/terraform-research/sydney-review.json`; revised one-worker calculation: `.logs/terraform-research/one-worker-costs.json`.

Saved-plan SHA-256: `4b6fae9ecf7b4196b994a6272b0619327484addff73fffd073b5a163d7a9dc4c`.

The committed [review data](INFRASTRUCTURE_REVIEW.json) contains a summary without the operator's IP or project identity. Local plan files are needed to review exact values; the summary cannot be applied. Regenerating the plan changes its checksum and requires a fresh review.

Checks passed: locked-provider initialization, `terraform fmt -check -recursive`, `terraform validate`, all **11 mocked infrastructure tests**, and the real authenticated plan. Mock test `apply` operations use fake providers and in-memory state; they do not create AWS resources. A successful plan verifies configuration and read access; it cannot guarantee every create permission, AZ capacity, node readiness, or application behavior. Those require deployment checks.

## Project and compatible versions

AWS CLI profile: `stockflow`. Selected Region: **Sydney, `ap-southeast-2`**. The toolkit/MCP service endpoint in `us-east-1` does not change the deployment Region. The Free Tier API confirmed an active **FREE** plan with **USD 100** remaining, expiring 15 April 2027. Credits can be consumed before then.

The operator's permanent role ARN was obtained with IAM `GetRole`; its `/managed/` path is required. Terraform uses that ARN for an EKS access entry rather than the temporary STS session ARN. No additional human IAM identity is created or modified.

| Component | Checked selection |
|---|---|
| Terraform | 1.16.5; supported configuration range >=1.16, <2 |
| AWS / TLS providers | 6.69.0 / 4.4.1; signed Windows and Linux checksums locked |
| EKS / kubectl | Kubernetes 1.36 / installed kubectl 1.36.1 |
| EKS standard support | Regional API confirms standard support through 2 August 2027 |
| Worker OS | EKS-optimized AL2023 x86_64; regional SSM release `1.36.4-20261012` exists and its AMI is free-plan eligible |
| Workers | One `m7i-flex.large`: 2 vCPUs and 8 GiB RAM; free-plan eligibility and availability in both selected AZs verified |
| VPC CNI | `v1.23.2-eksbuild.3` |
| CoreDNS | `v1.14.7-eksbuild.11` |
| kube-proxy | `v1.36.0-eksbuild.45` |
| EBS CSI driver | `v1.67.0-eksbuild.1` |
| Load Balancer Controller IAM policy | Vendored official `v3.6.0`; controller/chart installation belongs to Prompt 6 |

The saved plan fixes the four resolved add-on versions. An optional `addon_versions` map pins them across future plans. The node AMI release is AWS-selected for the requested Kubernetes/OS combination at creation; the checked SSM release is evidence, not a custom-AMI pin. Recheck versions, eligibility, and quotas if deploying much later. [EKS version lifecycle](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html), [EC2 free-plan instance types](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-free-tier-usage.html).

The earlier `t3.medium` proposal was changed because it is not free-plan eligible. `m7i-flex.large` provides memory for the later PostgreSQL, Prometheus, Grafana, and ArgoCD workloads while preserving the x86_64 images. Prompt 6 local checks pass for the complete small-demo bootstrap and app; actual EKS allocatable resources and scheduling still need deployment verification.

## Resources and security settings

- One VPC, `10.42.0.0/16`, with DNS enabled; no overlap with the existing default `172.31.0.0/16` VPC.
- Two AZs (`ap-southeast-2a` and `ap-southeast-2b`), each with a public and private /20 subnet, routes, and load-balancer discovery tags.
- One internet gateway, one zonal NAT gateway and Elastic IP, and an S3 gateway endpoint. Both private subnets share this NAT to limit demo cost. This creates a single-AZ egress dependency and possible cross-AZ transfer charges. `nat_mode=per_az` creates two gateways for better resilience at higher cost.
- One standard EKS control plane; private API enabled and public API restricted to this workstation's current public IPv4/32. Explicit operator access; no implicit creator administrator access.
- One managed node group with **min/desired/max = 1/1/2**, private workers, no SSH, encrypted 30 GiB gp3 root volumes, IMDSv2 required, metadata hop limit 1.
- Worker egress: HTTPS to external destinations through NAT; TCP/UDP DNS to the VPC resolver; pod/node traffic within the worker security group. Control-plane ingress permits API/kubelet/controller-webhook traffic as needed.
- A customer-managed KMS key with rotation for secrets and infrastructure logs; all five EKS control-plane log types and VPC flow logs, with seven-day retention.
- Six purpose-specific IAM roles: cluster, workers, VPC flow logs, CNI, EBS CSI, and Load Balancer Controller. Pod roles trust exact service-account subjects and STS audience through the cluster OIDC provider. CNI permissions stay off the worker role.
- AWS-managed EKS/node/ECR/CNI/EBS policies where appropriate; upstream controller policy retained with its resource-tag conditions. Some discovery actions require wildcard resources. Controller policy SHA-256: `16f232c9d9f79366fe949c4550ad517a202380058a9e48d45a4e215044a20a6a`.

The current regional On-Demand Standard quota is **5 vCPUs**, with no running or pending instances observed. The initial worker needs **2 vCPUs**; two workers would need **4 vCPUs**. A third worker would exceed the quota. Managed-node updates use **MINIMAL**, replacing a worker before launching its replacement. With one worker, node updates/failures temporarily take the application offline. Incompatible disruption budgets can block draining. Increase the quota before adding workers or switching to the default surge strategy. No quota increase was submitted. [Managed-node update behavior](https://docs.aws.amazon.com/eks/latest/userguide/managed-node-update-behavior.html).

EKS uses `support_type=STANDARD` to avoid extended-support rates; AWS can automatically upgrade the control plane at the end of standard support. This capstone should be cleaned up long before that. Cluster deletion protection is disabled to permit the planned cleanup.

The earlier two-worker plan is superseded by this one-worker plan. See [Prompt 6 checks](HELM.md) and the [bootstrap runbook](../k8s/bootstrap/README.md). The saved plan creates the EBS CSI add-on but no application PVCs. It provides controller IAM prerequisites but installs no Load Balancer Controller, ALB, Helm release, ArgoCD, or monitoring workload. Prompt 6 must explicitly pass the Region and VPC ID to the Load Balancer Controller because hop limit 1 prevents IMDS discovery from pods. No purchased domain is required; the later ALB-generated hostname is sufficient.

## Cost review

Current public USD on-demand rates were queried through AWS Price List on 15 October 2026 for Sydney. This is a usage estimate **before credits**, not a fixed-price quote. Monthly normalization uses 730 hours. The [machine-readable review](INFRASTRUCTURE_REVIEW.json) retains the rate SKUs, effective dates, and calculations.

| Planned infrastructure | Quantity / rate | Approx. USD/hour |
|---|---|---:|
| Standard-support EKS | 1 x $0.10/hour | 0.1000 |
| `m7i-flex.large` Linux worker | 1 x $0.1197/hour | 0.1197 |
| Zonal NAT gateway | 1 x $0.059/hour | 0.0590 |
| NAT public IPv4 | 1 x $0.005/hour | 0.0050 |
| Worker gp3 disk | 30 GiB x $0.096/GB-month | 0.0039 |
| KMS key | $1/key-month | 0.0014 |
| **Infrastructure baseline** | | **0.2890** |

The later demo adds roughly $0.0252/hour for one ALB, $0.0100/hour for two ALB public IPv4 addresses, $0.0080/hour for an **illustrative one LCU**, and $0.0013/hour for an **illustrative 10 GiB database disk**. Combined illustrative demo baseline: **$0.3335/hour**. The later chart may request different storage; ALB capacity usage and IP count vary with load and scaling.

| Running time | Infrastructure baseline | Illustrative later demo |
|---|---:|---:|
| 2 hours | $0.58 | $0.67 |
| 6 hours | $1.73 | $2.00 |
| 24 hours | $6.94 | $8.00 |
| 96 hours | $27.75 | $32.02 |
| 730 hours | $210.98 | $243.48 |

Additional usage is excluded: NAT processing **$0.059/GB**, internet/cross-AZ transfer, CloudWatch ingestion/storage, KMS requests, snapshots, extra storage/IOPS/throughput, extra nodes, and additional ALB capacity/IPs. NAT/ALB hourly minimums and partial-hour rounding can make short sessions cost more than simple multiplication. Existing free allowances and credit eligibility can reduce usage charged to credits; the estimate does not assume them.

For recording, plan a short **2–6 hour window** and reserve **$10 of credits as a working allowance**, then check actual usage. This allowance is a proposal, not an enforced cap. Keeping the environment for evaluation consumes credits continuously; four days of the illustrative baseline is about $32 before variable usage. A full month exceeds the current $100 balance. Remain on the free plan; any paid-plan upgrade needs a separate decision. The free plan ends when its credit/time limit is reached, so do not depend on it to keep the demo available indefinitely. [EKS pricing](https://aws.amazon.com/eks/pricing/), [VPC pricing](https://aws.amazon.com/vpc/pricing/), [ELB pricing](https://aws.amazon.com/elasticloadbalancing/pricing/), [AWS Pricing Calculator](https://calculator.aws/).

## Configuration scan findings requiring review

Trivy configuration scanning reports **3 CRITICAL, 0 HIGH** findings. The scan exits **1**. They remain visible and are not suppressed:

| Finding | Planned behavior and remaining risk |
|---|---|
| AWS-0040 | Public EKS API is enabled for workstation administration. It remains internet-facing, with IAM/EKS authorization and the IP allowlist. |
| AWS-0041 | The API allowlist contains a publicly routable IPv4/32. It is not `0.0.0.0/0`; Trivy still flags public CIDRs. A compromised allowlisted workstation can reach the endpoint. |
| AWS-0104 | Workers can reach any destination on TCP 443 to pull GHCR images and use AWS APIs. Other external ports are blocked, but HTTPS exfiltration remains possible. |

A stricter deployment would disable public API access and administer through an authenticated private network/management host, plus constrain outbound destinations through a suitable egress proxy/firewall or private registry/endpoints. That adds access infrastructure, operational work, and potentially cost. This short demo plan retains the documented settings for review. The image HIGH/CRITICAL gate from Prompt 4 remains unchanged; it is distinct from this configuration scan. **Do not describe Terraform as passing the configuration-security scan.**

## Review and later deployment

From `stockflow/`, load the tool environment if needed, then use the authenticated profile:

```powershell
. ..\Enter-Project.ps1
$env:AWS_PROFILE = 'stockflow'
$env:AWS_REGION = 'ap-southeast-2'
Set-Location terraform
terraform show -no-color 'stockflow.tfplan'
Get-FileHash -LiteralPath stockflow.tfplan -Algorithm SHA256
```

Before applying, review the exact target project, IAM role, IP allowlist, resource count, estimate, remaining scan findings, and cleanup window. If credentials expire, renew using `aws login --profile stockflow --region ap-southeast-2`. If the public IP, configuration, state, or reviewed values change, regenerate the plan and review it again. Keep credentials, tfvars, state, and binary/complete JSON plans out of Git.

Only after approval of the current plan:

```powershell
# From stockflow/terraform, with the environment above.
terraform apply 'stockflow.tfplan'
aws eks update-kubeconfig --profile stockflow --region ap-southeast-2 --name stockflow-eks
kubectl get nodes -o wide
kubectl get pods -n kube-system
```

If apply partially fails, preserve state, inspect the error, and create a fresh plan. Do not rerun a stale binary plan or create conflicting resources manually. The credential-free GitHub Terraform workflow validates schemas and runs mock tests; it never plans or applies against this project.

Local Terraform state lives at `terraform/terraform.tfstate`; retain a secure backup and the exact provider lockfile for cleanup. The workspace is inside OneDrive: confirm its access/sync settings before deployment because state and tfvars may be synced. They are excluded from Git, not automatically excluded from cloud sync. Move to a locking remote backend before shared operation.

## Cleanup after recording / required evaluation

Keep resources only for the agreed recording/evaluation window. First stop ArgoCD reconciliation and remove application Ingress/load balancers while their controller is still running. Back up required data, inspect reclaim policies, and intentionally remove disposable workloads/PVCs. Then review `terraform plan -destroy` and run `terraform destroy` from the same state.

Verify removal of EKS, workers, NAT/EIP, ALB/target groups, application EBS volumes, snapshots, and log groups. Terraform schedules its KMS key for deletion after seven days. Controller/PVC-created resources are not all recorded in Terraform state. Do not delete state until cleanup and resource verification succeed. Save the destroy evidence for grading.
