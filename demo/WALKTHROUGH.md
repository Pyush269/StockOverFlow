# Silent capstone walkthrough

[Watch/download the complete MP4](stockflow-walkthrough-silent.mp4).

No narration is needed. On-screen explanations and selectable captions describe the actual project evidence.

Duration: 00:11:12.680. Resolution: 1600 x 900. No audio track.

## Chapters

- **00:00:00** — Slides: project and architecture
- **00:01:51** — Live application
- **00:02:09** — Codebase structure
- **00:02:23** — Transactional inventory service
- **00:02:47** — Tests and containers
- **00:03:00** — Actual git push
- **00:03:12** — Live GitHub Actions run
- **00:03:14** — Pipeline progress
- **00:04:16** — Pipeline progress
- **00:06:42** — Pipeline progress
- **00:06:47** — Final GitHub result
- **00:07:10** — PostgreSQL tests and frontend build
- **00:07:28** — Build once and scan release images
- **00:07:46** — Publish scanned images to GHCR
- **00:08:04** — Terraform plan
- **00:08:18** — AWS Console: EKS
- **00:08:32** — AWS Console: VPC
- **00:08:49** — ArgoCD live application
- **00:09:16** — GitOps delivery
- **00:09:28** — Kubernetes pods
- **00:09:40** — Services and Ingress
- **00:09:53** — Application metrics
- **00:10:07** — Prometheus live Targets
- **00:10:34** — Grafana live dashboard

The pipeline section is the actual successful push-triggered run linked in the verification report. It ends at GHCR publication; the separate ArgoCD section explains how a Git values commit controls deployment.

AWS Console images are actual captured project screens. Command cards display real captured output and source excerpts. Optional installation, load, and recovery demonstrations are omitted.

After evaluation, perform and verify AWS cleanup and save destroy evidence. Cleanup has not yet been performed.
