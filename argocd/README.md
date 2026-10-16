# GitOps deployment

The production `stockflow` Application has been verified Synced/Healthy on EKS
in Sydney. [Recorded cloud stages](../docs/CLOUD_RUNTIME_VERIFICATION.json)
include promotion, a Git revert, and retained inventory after pod replacement.

ArgoCD renders the Helm chart and owns its resources. Run manual Helm commands
only in the separate disposable smoke namespace.

## Initial sync on a prepared cluster

From the repository root, with the EKS kubeconfig already configured:

```powershell
$stockflowContext = 'stockflow-eks-sydney'
kubectl --context $stockflowContext apply -f k8s/namespace.yaml
python scripts/create-k8s-secret.py --context $stockflowContext --namespace stockflow --release stockflow --values helm/stockflow/values-prod.yaml --secret-name stockflow-db
kubectl --context $stockflowContext apply -f argocd/project.yaml
kubectl --context $stockflowContext apply -f argocd/application.yaml
python scripts/gitops-sync.py --context $stockflowContext --application stockflow
# Enable reconciliation after checking the initial healthy deployment:
python scripts/gitops-sync.py --context $stockflowContext --application stockflow --enable-auto
```

The Secret helper generates credentials outside Git. The AppProject restricts
repository, namespaces, and resource types. Normal syncs run migration hooks.
The Application has no cascading deletion finalizer; deleting it alone does not
remove application data. Its local counterpart is used for isolated validation.

## Promote and roll back

1. Wait for the source commit's main CI run to pass tests/scans and publish both images.
2. Set both tags in `helm/stockflow/values-release.yaml` to that full source SHA.
3. Run `python scripts/test-gitops.py`, commit the values change, and push.
4. Confirm ArgoCD is Synced/Healthy and both deployed image tags match.
5. Revert the promotion commit and push to return to a compatible previous release.

Every main push runs CI. A new image publication does not change release values
or automatically promote itself. Image rollback does not reverse migrations.
HPA owns backend replica count; ArgoCD ignores only that field on the named
backend Deployment.

## Inspect

```powershell
kubectl --context stockflow-eks-sydney -n argocd get application stockflow
kubectl --context stockflow-eks-sydney -n argocd port-forward svc/argocd-server 8443:443
```

Open https://localhost:8443 and use the generated admin credentials locally.
