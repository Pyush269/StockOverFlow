# Working pipeline video

The silent pipeline recording follows a new push to `main`, then the actual
GitHub Actions tests, image-build/security gates, and GHCR publication. The
recorder uses a fresh browser with no saved sign-in, and a separate authorized
API monitor supplies sanitized job output. It never displays GitHub credentials.

The public run page and its changing status are recorded live. Source excerpts
and captured command/job output are labelled separately. No success state is
invented; the recorder stops with an error if the selected run fails.

This is the CI/CD chapter of the submission. The full walkthrough also needs the
slides, application/code, AWS Console, ArgoCD, Kubernetes, and monitoring.

Recording helper: `scripts/record-pipeline.mjs`. Intermediate metadata, raw video,
and API logs belong under ignored `.logs/pipeline-video/`. The MP4 has no audio so
the presenter can record their own narration.
