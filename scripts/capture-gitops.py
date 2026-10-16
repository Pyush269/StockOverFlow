"""Capture local ArgoCD evidence without printing or saving its credentials."""
import base64
import argparse
import json
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--cloud', action='store_true')
args = parser.parse_args()
context = 'stockflow-eks-sydney' if args.cloud else 'kind-stockflow-smoke'
application = 'stockflow' if args.cloud else 'stockflow-local'
kube = ['kubectl', '--context', context, '-n', 'argocd']
if args.cloud:
    outputs = json.loads(subprocess.check_output(['terraform', '-chdir=' + str(ROOT / 'terraform'), 'output', '-json'], text=True))
    config = json.loads(subprocess.check_output(kube + ['config', 'view', '--minify', '-o', 'json'], text=True))
    if outputs['region']['value'] != 'ap-southeast-2' or config['clusters'][0]['cluster']['server'] != outputs['cluster_endpoint']['value']:
        raise RuntimeError('Cloud context must match the applied Sydney cluster')
process = subprocess.Popen(kube + ['port-forward', '--address', '127.0.0.1', 'svc/argocd-server', '8443:443'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    time.sleep(3)
    if process.poll() is not None:
        raise SystemExit('Local ArgoCD port-forward failed; check port 8443')
    secret = json.loads(subprocess.check_output(kube + ['get', 'secret', 'argocd-initial-admin-secret', '-o', 'json']))
    password = base64.b64decode(secret['data']['password']).decode()
    result = subprocess.run(['node', str(ROOT / 'scripts/capture-gitops.mjs')], input=json.dumps({'password': password, 'application': application, 'cloud': args.cloud}), text=True, encoding='utf-8', errors='replace', capture_output=True)
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
