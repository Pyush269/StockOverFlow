# AWS infrastructure

StockFlow is deployed in Sydney (`ap-southeast-2`) using profile `stockflow`.
Terraform provisioning and cloud verification completed on 16 October 2026.
The original plan had 59 additions; the current recorded plan reports no changes.
The original OIDC provider denial was resolved with EKS Pod Identity.
[Actual AWS verification](AWS_VERIFICATION.json).

## Resources

- VPC `10.42.0.0/16`, two availability zones, two public and two private /20 subnets.
- One NAT gateway/EIP, internet gateway, and S3 gateway endpoint.
- EKS 1.36, private API plus public API restricted to the operator's IPv4/32.
- One private `m7i-flex.large` worker; node group min/desired/max 1/1/2.
  No public worker IP or SSH; IMDSv2 required, hop limit 1; encrypted 30 GiB gp3 root.
- Scoped Pod Identity roles for CNI, EBS CSI, and Load Balancer Controller.
- KMS encryption, control-plane logs, and VPC flow logs with seven-day retention.
- Kubernetes controllers create the public ALB and encrypted 10 GiB database EBS
  volume. Those resources are not all owned directly by Terraform state.

The chart runs two frontend and two backend replicas and a persistent PostgreSQL
StatefulSet. The one-worker design has no worker redundancy. A single NAT gateway
also creates a zonal dependency. Pod Identity uses the existing NAT HTTPS path.

## Reproduce or review

Use Terraform 1.16.5, AWS CLI, an authenticated `stockflow` profile, and the
committed provider lockfile. For a fresh deployment, copy
[terraform.tfvars.example](../terraform/terraform.tfvars.example) to the ignored
`terraform/terraform.tfvars`, then set the actual project ID, operator role,
and current public IPv4/32. Preserve the existing state and inputs on this workstation.

```powershell
$env:AWS_PROFILE = 'stockflow'
$env:AWS_REGION = 'ap-southeast-2'
terraform -chdir=terraform init -lockfile=readonly
terraform -chdir=terraform validate
terraform -chdir=terraform plan -input=false -out=stockflow-reviewed.tfplan
terraform -chdir=terraform show -no-color stockflow-reviewed.tfplan
# Apply only the reviewed current plan:
terraform -chdir=terraform apply stockflow-reviewed.tfplan
```

If configuration, state, IP allowlist, or credentials change, regenerate the plan.
Historical plans are evidence only. Do not apply them again. The credential-free
Terraform CI workflow validates HCL/provider schemas and runs mocked tests;
it does not provision AWS. Never commit credentials, real tfvars, state, kubeconfig,
or binary plans. Keep a secure state backup for cleanup.

## Reviewed operating estimate

The following is the reviewed 16 October 2026 Sydney estimate, before credits and
variable usage. It is not a spending cap or a current bill.

| Component | Approximate USD/hour |
|---|---:|
| Standard-support EKS | 0.1000 |
| One `m7i-flex.large` worker | 0.1197 |
| One NAT gateway | 0.0590 |
| NAT public IPv4 | 0.0050 |
| 30 GiB worker gp3 disk | 0.0039 |
| KMS key | 0.0014 |
| Infrastructure baseline | **0.2890** |
| Full demo including illustrative ALB capacity, IPv4, and database disk | **0.3335** |

The full-demo estimate is about $8 per day. NAT processing, transfer, logs,
KMS requests, snapshots, and additional capacity can increase it.
AWS continues running when the laptop or local Docker stops. No automatic
shutdown is configured. Use the agreed evaluation window, then clean up.

## Configuration scan findings

The recorded Trivy configuration scan reports three CRITICAL findings and exits
1. These remain documented and are not suppressed. Image vulnerability gates
are separate and passed for the recorded release.

| Finding | Configuration and remaining risk |
|---|---|
| AWS-0040 | Public EKS API enabled for administration, protected by IAM/EKS authorization and the operator IP allowlist. |
| AWS-0041 | The allowlist contains a publicly routable IPv4/32; it is not open to every IP. A compromised allowlisted workstation can reach the API. |
| AWS-0104 | Worker HTTPS egress permits external registries and AWS APIs, with remaining HTTPS exfiltration risk. |

A production environment should use suitable private administration, constrained
egress, authentication, HTTPS, redundancy, backups, and recovery procedures.
The current short demo retains the reviewed cost-conscious design.

## Cleanup after evaluation

Actual destroy completion evidence is pending because the live deployment remains
available for evaluation. Perform cleanup from the same authenticated project
and Terraform state after backing up any needed inventory:

1. Disable ArgoCD automated reconciliation. Remove the application Ingress while
   the Load Balancer Controller is still running, and verify the ALB is deleted.
2. Intentionally remove application workloads and disposable PVCs after checking
   reclaim policies and backups. Verify controller-created EBS volumes are removed.
3. Review `terraform -chdir=terraform plan -destroy`, then run
   `terraform -chdir=terraform destroy` against the same state.
4. Verify removal of EKS, workers, NAT/EIP, ALB/target groups, project-created EBS
   volumes/snapshots, and log groups. The KMS key has a seven-day deletion window.
5. Save the real destroy completion screenshot for grading. Retain state until
   resource removal has been verified.

Destroying the deployment removes its public URL. Source, slides, video, and the
Docker Compose setup remain usable afterward.
