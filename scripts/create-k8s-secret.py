"""Create an external database Secret without writing or printing credentials."""
import argparse
import base64
import json
import secrets
import subprocess
from pathlib import Path
from urllib.parse import quote, urlsplit

import yaml

ROOT = Path(__file__).resolve().parents[1]


def command(args, **kwargs):
    return subprocess.run(args, check=True, capture_output=True, text=True, **kwargs).stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context", required=True)
    parser.add_argument("--namespace", required=True)
    parser.add_argument("--release", required=True)
    parser.add_argument("--values", action="append", default=[])
    parser.add_argument("--secret-name", default="stockflow-db")
    args = parser.parse_args()
    helm = ["helm", "template", args.release, str(ROOT / "helm/stockflow"), "--namespace", args.namespace]
    for value in args.values:
        helm += ["--values", value]
    helm += ["--set-string", f"postgresql.existingSecret={args.secret_name}"]
    resources = [r for r in yaml.safe_load_all(command(helm)) if r]
    statefulset = next(r for r in resources if r["kind"] == "StatefulSet")
    container = statefulset["spec"]["template"]["spec"]["containers"][0]
    env = {e["name"]: e.get("value") for e in container["env"]}
    host = f'{statefulset["metadata"]["name"]}.{args.namespace}.svc.cluster.local'
    kubectl = ["kubectl", "--context", args.context, "--namespace", args.namespace]
    existing = command(kubectl + ["get", "secret", args.secret_name, "--ignore-not-found", "-o", "json"])
    if existing.strip():
        data = json.loads(existing)["data"]
        if not all(key in data for key in ["database-url", "postgres-password"]):
            raise SystemExit("Existing Secret is missing required keys; it was not changed")
        url = base64.b64decode(data["database-url"]).decode()
        parsed = urlsplit(url)
        if parsed.hostname != host or parsed.username != env["POSTGRES_USER"] or parsed.path != "/" + env["POSTGRES_DB"]:
            raise SystemExit("Existing Secret points to another database; choose a different Secret name")
        print(f"Kept existing Secret {args.secret_name}; credentials were not rotated")
        return
    password = secrets.token_hex(24)
    url = f'postgresql+psycopg://{quote(env["POSTGRES_USER"], safe="")}:{password}@{host}:5432/{env["POSTGRES_DB"]}'
    secret = {"apiVersion": "v1", "kind": "Secret", "metadata": {"name": args.secret_name, "namespace": args.namespace}, "type": "Opaque", "stringData": {"postgres-password": password, "database-url": url}}
    command(kubectl + ["create", "-f", "-"], input=json.dumps(secret))
    print(f"Created Secret {args.secret_name}; credentials were not printed or saved to disk")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        # Do not echo subprocess arguments or input containing credentials.
        raise SystemExit(f"Required Kubernetes/Helm command failed (exit {exc.returncode})") from None
