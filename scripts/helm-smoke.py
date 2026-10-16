"""Exercise the real Helm release, API proxy, migration upgrades, and PVC recovery."""
import argparse
import json
import subprocess
import time
import urllib.error
import urllib.request
import uuid
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context", required=True)
    parser.add_argument("--namespace", default="stockflow-smoke")
    parser.add_argument("--release", default="warehouse")
    parser.add_argument("--secret-name", default="stockflow-smoke-db")
    parser.add_argument("--values", action="append", default=[])
    parser.add_argument("--port", type=int, default=3001)
    parser.add_argument("--monitoring", action="store_true")
    args = parser.parse_args()
    # This test creates inventory and restarts PostgreSQL. It is for disposable releases only.
    if not args.namespace.endswith("-smoke"):
        raise SystemExit("Use a disposable namespace ending in -smoke")
    kube = ["kubectl", "--context", args.context, "-n", args.namespace]
    helm = ["helm", "upgrade", "--install", args.release, str(ROOT / "helm/stockflow"), "--kube-context", args.context, "--namespace", args.namespace]
    for path in args.values:
        helm += ["--values", path]
    helm += ["--set-string", f"postgresql.existingSecret={args.secret_name}"]
    # Smoke upgrades must never accidentally create an ALB from production values.
    helm += ["--set", "ingress.enabled=false", "--set", f"monitoring.serviceMonitor.enabled={str(args.monitoring).lower()}"]
    helm += ["--wait", "--wait-for-jobs", "--timeout", "10m"]

    def run(command):
        return subprocess.run(command, check=True, capture_output=True, text=True).stdout

    def get(kind, component=None):
        command = kube + ["get", kind, "-o", "json"]
        if component:
            command += ["-l", f"app.kubernetes.io/instance={args.release},app.kubernetes.io/component={component}"]
        return json.loads(run(command))["items"]

    def api(path, payload=None, method=None, expected=200):
        request = urllib.request.Request(f"http://127.0.0.1:{args.port}{path}", data=None if payload is None else json.dumps(payload).encode(), headers={"Content-Type": "application/json"}, method=method)
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                status, content = response.status, response.read()
        except urllib.error.HTTPError as exc:
            status, content = exc.code, exc.read()
        assert status == expected, (path, status, content.decode()[:300])
        return json.loads(content) if content else None

    @contextmanager
    def forward(service):
        logdir = ROOT / ".logs"
        logdir.mkdir(exist_ok=True)
        with (logdir / "helm-port-forward.log").open("w") as log:
            process = subprocess.Popen(kube + ["port-forward", "--address", "127.0.0.1", "svc/" + service, f"{args.port}:80"], stdout=log, stderr=subprocess.STDOUT)
            try:
                for _ in range(60):
                    if process.poll() is not None:
                        raise RuntimeError("Port-forward exited; inspect .logs/helm-port-forward.log")
                    try:
                        # Cloud port-forwards include the operator-to-Region round trip.
                        with urllib.request.urlopen(f"http://127.0.0.1:{args.port}/health", timeout=10) as response:
                            if response.status == 200:
                                break
                    except (urllib.error.URLError, TimeoutError):
                        time.sleep(1)
                else:
                    raise RuntimeError("Frontend port-forward did not become ready")
                yield
            finally:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)

    frontend = get("service", "frontend")[0]["metadata"]["name"]
    with forward(frontend):
        with urllib.request.urlopen(f"http://127.0.0.1:{args.port}/", timeout=10) as response:
            assert "StockFlow" in response.read().decode()
        product = api("/api/products", {"sku": "HELM-" + uuid.uuid4().hex[:10].upper(), "name": "Helm persistence proof", "unit_price": "19.99"}, expected=201)
        path = f'/api/products/{product["id"]}'
        assert api(path + "/movements", {"movement_type": "IN", "quantity": 10}, expected=201)["product"]["quantity"] == 10
        assert api(path + "/movements", {"movement_type": "OUT", "quantity": 3}, expected=201)["product"]["quantity"] == 7
        api(path + "/movements", {"movement_type": "OUT", "quantity": 8}, expected=409)
        assert api(path)["quantity"] == 7
        print("PASS: frontend, API proxy, stock-in/out and overselling protection")
        previous_jobs = {j["metadata"]["uid"] for j in get("jobs", "migration")}
        run(helm)
        assert api(path)["quantity"] == 7
        jobs = get("jobs", "migration")
        assert jobs and all(j.get("status", {}).get("succeeded", 0) == 1 for j in jobs)
        assert any(j["metadata"]["uid"] not in previous_jobs for j in jobs)
        print("PASS: Helm upgrade reran migration successfully and preserved stock")
        pvc = get("pvc")[0]
        assert pvc["status"]["phase"] == "Bound"
        db = get("pods", "postgres")[0]
        old_uid = db["metadata"]["uid"]
        run(kube + ["delete", "pod", db["metadata"]["name"], "--wait=true", "--timeout=60s"])
        for _ in range(90):
            replacements = get("pods", "postgres")
            if replacements and replacements[0]["metadata"]["uid"] != old_uid and any(c.get("type") == "Ready" and c.get("status") == "True" for c in replacements[0].get("status", {}).get("conditions", [])):
                break
            time.sleep(2)
        else:
            raise AssertionError("Replacement PostgreSQL pod did not become Ready")
        for _ in range(45):
            try:
                if api(path)["quantity"] == 7:
                    break
            except (AssertionError, urllib.error.URLError):
                time.sleep(2)
        else:
            raise AssertionError("Inventory did not recover after database pod replacement")
        assert get("pvc")[0]["metadata"]["uid"] == pvc["metadata"]["uid"]
        print("PASS: PostgreSQL pod replacement reused the PVC and preserved inventory")
        for component in ["backend", "frontend"]:
            deployments = get("deployments", component)
            assert deployments[0]["status"].get("readyReplicas", 0) >= 2
        print("PASS: at least two Ready backend and frontend replicas")
        result = {"context": args.context, "namespace": args.namespace, "release": args.release, "product_id": product["id"], "quantity_after_restart": 7, "pvc_bound": True, "migration_runs_verified": 2, "replicas_ready": {"backend": 2, "frontend": 2}}
        (ROOT / ".logs/helm-runtime.json").write_text(json.dumps(result, indent=2) + "\n")
    print("Helm runtime verification passed; the disposable release remains available for inspection")


if __name__ == "__main__":
    main()
