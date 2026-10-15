"""Render chart variants and check cross-resource behavior without AWS credentials."""
import json
import subprocess
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CHART = ROOT / "helm/stockflow"


def render(*extra, release="warehouse", namespace="warehouse-lab", fail=False):
    result = subprocess.run(["helm", "template", release, str(CHART), "--namespace", namespace, "--kube-version", "1.36.4", *extra], capture_output=True, text=True)
    if fail:
        return result
    if result.returncode:
        raise AssertionError(result.stderr)
    return [r for r in yaml.safe_load_all(result.stdout) if r]


def kind(resources, name):
    return [r for r in resources if r["kind"] == name]


class ChartTests(unittest.TestCase):
    def test_services_and_ingress_match_for_arbitrary_release(self):
        resources = render("-f", str(CHART / "values-prod.yaml"))
        services = {r["metadata"]["name"]: r for r in kind(resources, "Service")}
        for path in kind(resources, "Ingress")[0]["spec"]["rules"][0]["http"]["paths"]:
            target = path["backend"]["service"]
            service = services[target["name"]]
            self.assertEqual(service["spec"].get("type", "ClusterIP"), "ClusterIP")
            self.assertEqual(target["port"]["number"], service["spec"]["ports"][0]["port"])
        self.assertEqual([p["path"] for p in kind(resources, "Ingress")[0]["spec"]["rules"][0]["http"]["paths"]], ["/api", "/"])
        self.assertTrue(all(r["metadata"]["namespace"] == "warehouse-lab" for r in resources))

    def test_database_before_sync_migration_before_applications(self):
        resources = render()
        db = kind(resources, "StatefulSet")[0]
        job = kind(resources, "Job")[0]
        self.assertEqual(db["metadata"]["annotations"]["argocd.argoproj.io/sync-wave"], "-1")
        self.assertEqual(job["metadata"]["annotations"]["argocd.argoproj.io/hook"], "Sync")
        self.assertNotIn("helm.sh/hook", job["metadata"]["annotations"])
        self.assertEqual(job["metadata"]["annotations"]["argocd.argoproj.io/sync-wave"], "0")
        for app in kind(resources, "Deployment"):
            self.assertEqual(app["metadata"]["annotations"]["argocd.argoproj.io/sync-wave"], "1")
        backend = next(d for d in kind(resources, "Deployment") if d["metadata"]["labels"]["app.kubernetes.io/component"] == "backend")
        self.assertEqual(backend["spec"]["template"]["spec"]["initContainers"][0]["command"], ["python", "/bootstrap/wait-for-schema.py"])

    def test_non_root_and_pull_secrets_cover_every_pod(self):
        resources = render("--set", "imagePullSecrets[0].name=registry-login")
        for r in resources:
            if r["kind"] not in ["Deployment", "StatefulSet", "Job"]:
                continue
            pod = r["spec"]["template"]["spec"]
            self.assertFalse(pod["automountServiceAccountToken"])
            self.assertTrue(pod["securityContext"]["runAsNonRoot"])
            self.assertEqual(pod["imagePullSecrets"], [{"name": "registry-login"}])
            for c in pod["containers"] + pod.get("initContainers", []):
                self.assertFalse(c["securityContext"]["allowPrivilegeEscalation"])
                self.assertTrue(c["securityContext"]["readOnlyRootFilesystem"])
                self.assertEqual(c["securityContext"]["capabilities"]["drop"], ["ALL"])
                self.assertIn("memory", c["resources"]["requests"])
                self.assertIn("cpu", c["resources"]["limits"])

    def test_matching_images_and_external_credentials(self):
        resources = render()
        self.assertFalse(kind(resources, "Secret"))
        job = kind(resources, "Job")[0]["spec"]["template"]["spec"]["containers"][0]
        backend = next(d for d in kind(resources, "Deployment") if d["metadata"]["labels"]["app.kubernetes.io/component"] == "backend")["spec"]["template"]["spec"]
        self.assertEqual(job["image"], backend["containers"][0]["image"])
        self.assertEqual(job["image"], backend["initContainers"][0]["image"])
        self.assertIn("secretKeyRef", job["env"][0]["valueFrom"])

    def test_hpa_and_scraping_use_the_real_backend_service(self):
        resources = render("-f", str(CHART / "values-prod.yaml"))
        hpa = kind(resources, "HorizontalPodAutoscaler")[0]
        self.assertEqual(hpa["spec"]["minReplicas"], 2)
        self.assertLessEqual(hpa["spec"]["minReplicas"], hpa["spec"]["maxReplicas"])
        self.assertNotIn("replicas", next(d for d in kind(resources, "Deployment") if d["metadata"]["name"] == hpa["spec"]["scaleTargetRef"]["name"])["spec"])
        monitor = kind(resources, "ServiceMonitor")[0]
        service = next(s for s in kind(resources, "Service") if all(s["metadata"]["labels"].get(k) == v for k, v in monitor["spec"]["selector"]["matchLabels"].items()))
        self.assertEqual(monitor["spec"]["endpoints"][0]["port"], service["spec"]["ports"][0]["name"])
        self.assertEqual(monitor["spec"]["endpoints"][0]["path"], "/metrics")

    def test_persistence_and_local_overrides(self):
        resources = render("-f", str(CHART / "values-local.yaml"), "--set", "autoscaling.enabled=false")
        db = kind(resources, "StatefulSet")[0]
        self.assertEqual(db["spec"]["replicas"], 1)
        self.assertEqual(db["spec"]["persistentVolumeClaimRetentionPolicy"]["whenDeleted"], "Retain")
        self.assertEqual(db["spec"]["volumeClaimTemplates"][0]["spec"]["storageClassName"], "standard")
        self.assertFalse(kind(resources, "Ingress"))
        self.assertFalse(kind(resources, "ServiceMonitor"))
        self.assertFalse(kind(resources, "HorizontalPodAutoscaler"))
        self.assertTrue(all(d["spec"]["replicas"] == 2 for d in kind(resources, "Deployment")))

    def test_long_names_are_valid_and_service_references_still_resolve(self):
        resources = render("-f", str(CHART / "values-prod.yaml"), release="a" * 53)
        self.assertTrue(all(len(r["metadata"]["name"]) <= 63 for r in resources))
        service_names = {s["metadata"]["name"] for s in kind(resources, "Service")}
        for path in kind(resources, "Ingress")[0]["spec"]["rules"][0]["http"]["paths"]:
            self.assertIn(path["backend"]["service"]["name"], service_names)

    def test_invalid_release_values_fail_before_install(self):
        for extra in [("--set", "backend.image.tag=latest"), ("--set", "frontend.replicas=1"), ("--set", "autoscaling.minReplicas=5"), ("--set-string", "frontend.image.tag=" + "a" * 40), ("--set", "postgresql.existingSecret=")]:
            self.assertNotEqual(render(*extra, fail=True).returncode, 0, extra)


if __name__ == "__main__":
    unittest.main(verbosity=2)
