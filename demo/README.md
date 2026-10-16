# Submission artifacts

- [slides.pdf](slides.pdf): 11-slide deck using actual verified cloud evidence.
- [SLIDES.md](SLIDES.md): editable content and speaker guidance.
- [Silent pipeline video](stockflow-pipeline-silent.mp4): actual push-to-main
  CI run and successful publication; **CI/CD chapter only**, ready for your voice.
  See the [narration guide](PIPELINE_NARRATION.md) and [video details](PIPELINE_VIDEO.md).
- [RECORDING.md](RECORDING.md): walkthrough order, verified cloud evidence, and
  evaluation/cleanup checklist. The full narrated walkthrough is still pending.

The rubric accepts PDF slides. Before final submission, record the personal walkthrough using the verified cloud results.

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

The silent pipeline chapter is already committed in this directory and linked
from the main README. Add the complete narrated walkthrough here, or as a GitHub
release asset, and link it before final submission. Add actual destroy evidence
when cleanup runs after the agreed evaluation window.
