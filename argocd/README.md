# StockFlow GitOps

The production `stockflow` Application is deployed on EKS in Sydney and verified Synced/Healthy, with cloud image promotion, Git revert rollback, and retained inventory. See [cloud evidence](../docs/CLOUD_VERIFICATION.md). `application-local.yaml` targets the separate local demo namespace.

ArgoCD renders Helm and owns the resulting resources. Do not run `helm upgrade`
against its application. The earlier manual Helm smoke release is separate
evidence; it was uninstalled locally before starting GitOps, retaining its PVC.

## First sync

Create the destination namespace and database Secret before applying the
Application. The AppProject permits only this repository, two named namespaces,
and the chart's namespace-scoped resource types. It cannot create Secrets or
cluster infrastructure. There is no cascading deletion finalizer on the
Application; deleting it alone preserves application resources and inventory.

For the existing isolated local cluster, from `stockflow/`:

```powershell
$env:KUBECONFIG = Join-Path $PWD '.logs/kind.kubeconfig'
# Namespace/Secret preparation is idempotent except the explicit create command.
kubectl --context kind-stockflow-smoke create namespace stockflow-gitops-smoke
kubectl --context kind-stockflow-smoke label namespace stockflow-gitops-smoke pod-security.kubernetes.io/enforce=restricted pod-security.kubernetes.io/enforce-version=v1.36 --overwrite
python scripts/create-k8s-secret.py --context kind-stockflow-smoke --namespace stockflow-gitops-smoke --release stockflow --values helm/stockflow/values-local.yaml --secret-name stockflow-gitops-db
kubectl --context kind-stockflow-smoke apply -f argocd/project.yaml
kubectl --context kind-stockflow-smoke apply -f argocd/application-local.yaml
python scripts/gitops-sync.py --context kind-stockflow-smoke --application stockflow-local
```

The first sync is manual. Once it is Synced/Healthy, rerun the last command with
`--enable-auto` to enable pruning/self-heal with `allowEmpty: false`. The helper
waits for the operation and health with a ten-minute bound. Normal syncs run
migration hooks; do not use selective sync to bypass them.

For EKS, after deployment approval and bootstrap, prepare namespace `stockflow`
and Secret `stockflow-db` using release `stockflow` and production values. Apply
`project.yaml` and `application.yaml`, then run the helper against the explicit
EKS context/application `stockflow`. The first Ingress sync creates a billable
ALB; **do not run it while AWS is meant to stay off**.

## Promotion and rollback

Both Applications read the shared `helm/stockflow/values-release.yaml` after
their environment overlay. That file sets both full source SHA tags. Verify the
source commit's successful main **StockFlow CI** run, including registry
publication, before editing either tag. A source commit and the later release
values commit are different commits.

1. Build/test/scan/publish the source commit through CI.
2. Change both image tags in `values-release.yaml` to its exact 40-character SHA.
3. Run `python scripts/test-gitops.py` and commit/push that values change.
4. ArgoCD observes Git and syncs it. Confirm Synced/Healthy and the actual Pod
   images match the release file, then exercise the API.
5. For rollback, revert the promotion commit with `git revert <promotion-commit>`
   and push. Observe ArgoCD reconciling back to the compatible previous SHA.

Image rollback does not reverse migrations. This first demonstration uses
releases with the same application and schema. Destructive migrations need a
separate backup/compatibility plan. The CI workflow ignores Helm/GitOps-only
changes, so values commits do not produce a build/promotion loop. The Helm
workflow still validates changed release values. Actions does not deploy AWS or
the ArgoCD application.

HPA owns backend replicas: the chart omits `spec.replicas` when HPA is enabled,
and the Application ignores only that field on its named backend Deployment
with `RespectIgnoreDifferences=true`. Other drift remains visible.

## Local demonstration recorded

The [runtime report](../docs/GITOPS_VERIFICATION.json) records baseline,
promotion, actual Git revert, and backend Pod recovery. The promotion commit is
`88b3cd0`; its revert is `1bbfa84`. Both frontend/backend image tags changed from
the published `71a3654` source SHA to published `537fa26` and back. The migration
hook succeeded, both Deployments retained at least two Ready replicas, and
quantity 7 remained on the same PVC. The two application/schema source trees
are unchanged between these releases. This demonstrates compatible image
rollback, not database downgrade or recovery from a worker failure.

The [ArgoCD screenshot](../docs/screenshots/stockflow-argocd-local.png) shows the
real local Application Healthy/Synced with auto sync enabled. During development,
the helper's apply-only strategy skipped migration hooks; it was corrected to
hook strategy. Manual sync also carries the configured retry policy so first
HPA metric samples can arrive. HPA is in wave 2 after workload readiness. These
fixes were retested; real EKS verification remains pending.

Official references: [Helm integration](https://argo-cd.readthedocs.io/en/stable/user-guide/helm/),
[sync options](https://argo-cd.readthedocs.io/en/stable/user-guide/sync-options/),
[projects](https://argo-cd.readthedocs.io/en/stable/user-guide/projects/).
