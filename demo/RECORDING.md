# Walkthrough recording

The [complete silent walkthrough](stockflow-walkthrough-silent.mp4) uses clear
on-screen explanations and captions. **No narration is needed.** See its
[chapters and sources](WALKTHROUGH.md). The [separate CI/CD chapter](stockflow-pipeline-silent.mp4)
is also available. Never show passwords, tokens, `.env`, kubeconfig, Terraform
state, or Secret contents.

## Recording order

1. **Slides** — problem, architecture, stack, infrastructure, and observability.
2. **Codebase** — folder structure, key files, transactional service, test output,
   Dockerfile, and a brief view of the working application.
3. **CI/security and registry** — successful main run, strict image scan gate,
   reports and both SHA image tags. Explain the separate Terraform findings.
4. **Terraform and AWS** — execute a real read-only plan, show the historical
   original provisioning plan, and actual AWS Console VPC/EKS views.
5. **ArgoCD** — repository/path/values, Synced/Healthy, matching image SHA,
   promotion commit and compatible rollback.
6. **Kubernetes** — execute the healthy pods, Services, and Ingress commands.
7. **Prometheus** — `/metrics` and the Targets page showing the app as UP.
8. **Grafana** — the live dashboard with populated application metrics.

The final edit includes the required sections only. It omits optional installation,
load, and recovery demonstrations. Credentials are handled outside recorded pages.

The localhost verification viewer streams stdout from a fixed allowlist of real
processes; it does not synthesize command results. Source excerpts and historical
plan/Helm evidence are labelled separately. Additional required screenshots live
in the [grading evidence index](../docs/GRADING_EVIDENCE.md), keeping the video
focused on the specified walkthrough order.

## Actual cloud evidence and recording checklist

- [x] Reviewed plan refreshed for current operator IP and actual profile/session.
- [x] Terraform apply and Ready EKS worker recorded.
- [x] EBS CSI Pod Identity and Bound encrypted gp3 application PVC verified.
- [x] Real Helm smoke release evidence captured, then smoke workload removed.
- [x] AWS Load Balancer Controller and public ALB frontend/API checks pass.
- [x] Cloud ArgoCD sync, image promotion/rollback, and recovery captured.
- [x] Cloud Prometheus/Grafana and HPA metrics verified.
- [x] PDF deck updated from `SLIDES.md` with verified cloud results and real screenshots.
- [x] Complete silent walkthrough saved, with chapters, captions, and verification.
- [x] Repository link and complete video download verified in a fresh signed-out browser.
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

Technical reports and screenshots: [cloud verification](../docs/CLOUD_VERIFICATION.md). The walkthrough includes actual AWS Console captures, real command output, live admin screens, and the successful pipeline recording. Use only the project resources in Sydney and avoid showing credentials.
