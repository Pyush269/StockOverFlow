# Walkthrough recording

The [silent CI/CD chapter](stockflow-pipeline-silent.mp4) is recorded, with a
[narration guide](PIPELINE_NARRATION.md). Add your voice and the other required
sections to complete the submission walkthrough. Never show passwords,
tokens, `.env`, kubeconfig, Terraform state, or Secret contents.

## Recording order

1. **Slides and working application** — problem, architecture, StockFlow screens.
   Create a product, receive 10, issue 3, reject 8, show quantity 7 and history.
2. **Codebase and tests** — transactional service, Alembic, tests, Dockerfiles,
   Compose. Show the existing passing test output.
3. **CI/security and registry** — successful main run, strict image scan gate,
   reports and both SHA image tags. Explain the separate Terraform findings.
4. **Terraform and AWS** — show the reviewed plan, real VPC/EKS/node group,
   private worker placement, IAM role boundaries, and current usage estimate.
5. **ArgoCD** — repository/path/values, Synced/Healthy, matching image SHA,
   promotion commit and compatible rollback.
6. **Kubernetes** — manual Helm smoke evidence, two frontend/backend replicas,
   migrations, PVC, Services, Ingress hostname, and live application/API.
7. **Prometheus** — `/metrics`, UP targets, and real query results.
8. **Grafana and recovery** — live panels, bounded load, observed HPA changes,
   replacement backend pod, and inventory retained through recovery.

Suggested length: 8–12 minutes unless the instructor specifies otherwise. Rehearse
once and keep browser tabs/terminal commands ready. Pause recording when handling
credentials. Avoid recording installation wait time.

## Actual cloud evidence and recording checklist

- [x] Reviewed plan refreshed for current operator IP and actual profile/session.
- [x] Terraform apply and Ready EKS worker recorded.
- [x] EBS CSI Pod Identity and Bound encrypted gp3 application PVC verified.
- [x] Real Helm smoke release evidence captured, then smoke workload removed.
- [x] AWS Load Balancer Controller and public ALB frontend/API checks pass.
- [x] Cloud ArgoCD sync, image promotion/rollback, and recovery captured.
- [x] Cloud Prometheus/Grafana and HPA metrics verified.
- [x] PDF deck updated from `SLIDES.md` with verified cloud results and real screenshots.
- [ ] Walkthrough video saved or uploaded with an accessible submission link.
- [ ] Repository and video access checked from another browser/device.
- [ ] Cleanup timing agreed with instructor; destroy evidence saved afterward.

## Evaluation and cleanup

Keep the live demo available until evaluation finishes unless the instructor
accepts recording-only assessment. After evaluation: save needed inventory,
stop ArgoCD reconciliation, remove the Ingress while its controller is running,
verify ALB deletion, remove workloads/disposable PVCs intentionally, run the
reviewed Terraform destroy, and verify no project-created billable resources
remain. Follow `docs/INFRASTRUCTURE.md`; deleting a local ZIP or stopping Docker
does not stop AWS resources.

The source submission document gives 19 October 2026 at 11:59 PM IST but calls it
Sunday; that date is Monday. Confirm the intended deadline with the instructor.
Source: https://github.com/Nency-Ravaliya/devsecops-python/blob/main/SUBMISSION.md

Actual cloud URL: http://k8s-stockflo-stockflo-96a126ddd5-1324338338.ap-southeast-2.elb.amazonaws.com

Technical reports and screenshots: [cloud verification](../docs/CLOUD_VERIFICATION.md). These reports are ready to show; the AWS Console views and personal narrated walkthrough still need recording. Use only the project resources in Sydney and avoid showing credentials.
