# Submission artifacts

- [Complete silent walkthrough](stockflow-walkthrough-silent.mp4): slides, code,
  actual push/CI, Terraform and AWS Console, ArgoCD, Kubernetes, Prometheus
  Targets, and Grafana, in the required order. No narration is needed.
  See [chapters and sources](WALKTHROUGH.md) and [verification](WALKTHROUGH_VERIFICATION.json).
- [slides.pdf](slides.pdf): 11-slide deck using actual verified cloud evidence.
- [SLIDES.md](SLIDES.md): editable content and speaker guidance.
- [Silent pipeline video](stockflow-pipeline-silent.mp4): actual push-to-main
  CI run and successful publication; a separate **CI/CD chapter only**.
  See the [optional explanation notes](PIPELINE_NARRATION.md) and [video details](PIPELINE_VIDEO.md).
- [RECORDING.md](RECORDING.md): walkthrough order, verified cloud evidence, and
  evaluation/cleanup checklist.
- [Grading evidence index](../docs/GRADING_EVIDENCE.md): module-by-module source,
  screenshots, and actual verification results.

The rubric accepts PDF slides. Submit the repository link with the complete
silent walkthrough and PDF above. The video uses on-screen explanations and
captions, as requested by the presenter.

To regenerate after updating the verification reports, use a separate docs
environment or the project's existing environment:

```powershell
python -m pip install -r demo/requirements.txt
python demo/build-slides.py
```

The generator reads `docs/CLOUD_RUNTIME_VERIFICATION.json`,
`docs/CLOUD_OBSERVABILITY_VERIFICATION.json`, and committed actual screenshots. It
refuses to claim release/rollback/recovery or scaling without the corresponding
recorded results. Review the output visually after changes. Do not edit evidence
JSON to invent observations.

The complete walkthrough and separate pipeline chapter belong in this directory
and are linked from the main README. Add actual destroy evidence when cleanup
runs after the agreed evaluation window. Cleanup has not happened yet.
