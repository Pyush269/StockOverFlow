"""Capture local ArgoCD evidence without printing or saving its credentials."""
import base64
import json
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
kube = ['kubectl', '--context', 'kind-stockflow-smoke', '-n', 'argocd']
process = subprocess.Popen(kube + ['port-forward', '--address', '127.0.0.1', 'svc/argocd-server', '8443:443'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    time.sleep(3)
    if process.poll() is not None:
        raise SystemExit('Local ArgoCD port-forward failed; check port 8443')
    secret = json.loads(subprocess.check_output(kube + ['get', 'secret', 'argocd-initial-admin-secret', '-o', 'json']))
    password = base64.b64decode(secret['data']['password']).decode()
    result = subprocess.run(['node', str(ROOT / 'scripts/capture-gitops.mjs')], input=json.dumps({'password': password}), text=True, encoding='utf-8', errors='replace', capture_output=True)
    if result.returncode:
        (ROOT / '.logs/argocd-browser-error.txt').write_text(result.stderr.replace(password, '[redacted]'), encoding='utf-8')
        raise SystemExit('Local ArgoCD browser capture failed; inspect the private error log')
    print(result.stdout, end='')
finally:
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)
