# Working pipeline video

- [Silent MP4](stockflow-pipeline-silent.mp4): **6 minutes 18 seconds**, H.264,
  1600 x 900, no audio track. Includes chapter markers and selectable captions.
- [Narration guide](PIPELINE_NARRATION.md): suggested wording and chapter times.
- [Separate captions](stockflow-pipeline-silent.srt) for a video editor.
- [Verification record](PIPELINE_VIDEO_VERIFICATION.json).

Actual recorded run: [StockFlow CI #13](https://github.com/Pyush269/StockOverFlow/actions/runs/38867618119).
The new push used source commit `e207e786c6df07b2f270b1d5120a5fc78b8edfc1`.
All three jobs passed, including 49 backend tests, 11 frontend unit tests,
both strict image scan gates, and GHCR publication. The CI run itself took
2 minutes 39 seconds; the video also includes source explanations and results.

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

The MP4 was decoded end to end and representative frames were visually checked.
To encode the preserved raw recording again, install the optional
`demo/video-requirements.txt` dependencies and run `python demo/encode-pipeline.py`.
The encoder requires a real successful three-job run and its recorded metadata;
it does not generate a successful result from a template.
