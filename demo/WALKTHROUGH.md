# Silent capstone walkthrough

[Watch/download the complete MP4](stockflow-walkthrough-silent.mp4).

No narration is needed. On-screen explanations and selectable captions describe the actual project evidence.

Duration: 00:12:13.080. Resolution: 1600 x 900. No audio track.

## Chapters

- **00:00:00** — Slides: project and architecture
- **00:01:50** — Live application
- **00:02:09** — Codebase structure
- **00:02:23** — Transactional inventory service
- **00:02:46** — Tests and containers
- **00:02:59** — Actual git push
- **00:03:11** — Live GitHub Actions run
- **00:03:13** — Pipeline progress
- **00:04:15** — Pipeline progress
- **00:06:41** — Pipeline progress
- **00:06:46** — Final GitHub result
- **00:07:09** — PostgreSQL tests and frontend build
- **00:07:27** — Build once and scan release images
- **00:07:45** — Publish scanned images to GHCR
- **00:08:03** — Terraform plan: live execution
- **00:09:07** — Original provisioning plan
- **00:09:19** — AWS Console: EKS
- **00:09:33** — AWS Console: VPC
- **00:09:49** — ArgoCD live application
- **00:10:15** — GitOps delivery
- **00:10:27** — Kubernetes pods: live execution
- **00:10:42** — Services and Ingress: live execution
- **00:10:54** — Application metrics
- **00:11:09** — Prometheus live Targets
- **00:11:35** — Grafana live dashboard

The pipeline section is the actual successful push-triggered run linked in the verification report. It ends at GHCR publication; the separate ArgoCD section explains how a Git values commit controls deployment.

Terraform and Kubernetes commands execute during the recording, with stdout streamed from real processes. AWS Console images are actual captured project screens. Source excerpts and the original provisioning plan are labelled separately; the original plan is historical and must not be reapplied. Optional installation, load, and recovery demonstrations are omitted.

Additional required screenshots and their sources are linked in the [grading evidence index](../docs/GRADING_EVIDENCE.md).

After evaluation, perform and verify AWS cleanup and save destroy evidence. Cleanup has not yet been performed.
