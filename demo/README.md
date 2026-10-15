# Submission artifacts

- [slides.pdf](slides.pdf): 11-slide deck using actual local evidence. AWS slides
  explicitly show deployment pending.
- [SLIDES.md](SLIDES.md): editable content and speaker guidance.
- [RECORDING.md](RECORDING.md): walkthrough order, pending cloud evidence, and
  evaluation/cleanup checklist. The mandatory video is not recorded yet.

The rubric accepts PDF slides. Before final submission, update the deck with
verified cloud results and record the walkthrough; local screenshots do not
prove EKS/ALB deployment.

To regenerate after updating the verification reports, use a separate docs
environment or the project's existing environment:

```powershell
python -m pip install -r demo/requirements.txt
python demo/build-slides.py
```

The generator reads `docs/GITOPS_VERIFICATION.json`,
`docs/OBSERVABILITY_VERIFICATION.json`, and committed actual screenshots. It
refuses to claim release/rollback/recovery or scaling without the corresponding
recorded results. Review the output visually after changes. Do not edit evidence
JSON to invent observations.

Upload the video under this directory, or as a GitHub release asset and link it
here. The repository is not a complete submission until the video/cloud evidence
and post-evaluation cleanup evidence are present.
