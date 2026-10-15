"""Verify an actual disposable GitOps release, retained inventory, and pod recovery."""
import argparse
import json
import subprocess
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--context', required=True)
    parser.add_argument('--namespace', default='stockflow-gitops-smoke')
    parser.add_argument('--application', default='stockflow-local')
    parser.add_argument('--expected-sha', required=True)
    parser.add_argument('--stage', choices=['baseline', 'release', 'rollback', 'recovery'], required=True)
    args = parser.parse_args()
    if not args.namespace.endswith('-smoke'):
        parser.error('Use a disposable namespace ending in -smoke')
    kube = ['kubectl', '--context', args.context]

    def run(tail):
        return subprocess.check_output(kube + tail, text=True)

    def resources(kind, component=None):
        command = ['-n', args.namespace, 'get', kind, '-o', 'json']
        if component:
            command += ['-l', 'app.kubernetes.io/instance=stockflow,app.kubernetes.io/component=' + component]
        return json.loads(run(command))['items']

    app = json.loads(run(['-n', 'argocd', 'get', 'application', args.application, '-o', 'json']))
    assert app['status']['sync']['status'] == 'Synced' and app['status']['health']['status'] == 'Healthy'
    assert any(r['kind'] == 'Job' and r.get('hookPhase') == 'Succeeded' for r in app['status']['operationState']['syncResult']['resources']), 'Migration hook did not succeed'
    for component in ['backend', 'frontend']:
        run(['-n', args.namespace, 'rollout', 'status', 'deployment/stockflow-stockflow-' + component, '--timeout=180s'])
        deployment = resources('deployments', component)[0]
        assert deployment['status'].get('readyReplicas', 0) >= 2
        assert deployment['spec']['template']['spec']['containers'][0]['image'].endswith(':' + args.expected_sha)
    state_path = ROOT / '.logs/gitops-runtime-state.json'
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    pvc = resources('pvc')[0]
    assert pvc['status']['phase'] == 'Bound'
    process = subprocess.Popen(kube + ['-n', args.namespace, 'port-forward', '--address', '127.0.0.1', 'svc/stockflow-stockflow-frontend', '3001:80'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def api(path, data=None, expected=200):
        request = urllib.request.Request('http://127.0.0.1:3001' + path, data=None if data is None else json.dumps(data).encode(), headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                status, body = response.status, response.read()
        except urllib.error.HTTPError as error:
            status, body = error.code, error.read()
        assert status == expected, (path, status)
        return json.loads(body)

    try:
        for _ in range(40):
            if process.poll() is not None:
                raise RuntimeError('Frontend port-forward failed; check for a busy port 3001')
            try:
                api('/api/dashboard')
                break
            except (urllib.error.URLError, AssertionError):
                time.sleep(1)
        else:
            raise RuntimeError('Frontend API did not become available')
        if args.stage == 'baseline':
            product = api('/api/products', {'sku': 'GITOPS-' + uuid.uuid4().hex[:8].upper(), 'name': 'GitOps retained inventory', 'unit_price': '49.99'}, 201)
            path = f'/api/products/{product["id"]}'
            api(path + '/movements', {'movement_type': 'IN', 'quantity': 10}, 201)
            api(path + '/movements', {'movement_type': 'OUT', 'quantity': 3}, 201)
            api(path + '/movements', {'movement_type': 'OUT', 'quantity': 8}, 409)
            state = {'namespace': args.namespace, 'product_id': product['id'], 'pvc_uid': pvc['metadata']['uid'], 'stages': []}
        assert state['namespace'] == args.namespace
        assert pvc['metadata']['uid'] == state['pvc_uid']
        if args.stage == 'recovery':
            before = resources('pods', 'backend')
            old_uids = {pod['metadata']['uid'] for pod in before}
            run(['-n', args.namespace, 'delete', 'pod', before[0]['metadata']['name'], '--wait=true', '--timeout=60s'])
            for _ in range(90):
                pods = resources('pods', 'backend')
                ready = [pod for pod in pods if not pod['metadata'].get('deletionTimestamp') and any(c['type'] == 'Ready' and c['status'] == 'True' for c in pod.get('status', {}).get('conditions', []))]
                if len(ready) >= 2 and any(pod['metadata']['uid'] not in old_uids for pod in ready):
                    break
                time.sleep(2)
            else:
                raise AssertionError('Replacement backend pod did not become Ready')
        assert api(f'/api/products/{state["product_id"]}')["quantity"] == 7
        result = {'stage': args.stage, 'sync': 'Synced', 'health': 'Healthy', 'git_revision': app['status']['sync']['revision'], 'image_source_sha': args.expected_sha, 'quantity': 7, 'pvc_unchanged': True, 'migration_hook': 'Succeeded', 'ready_frontend_and_backend_replicas': 'at least 2'}
        state['stages'].append(result)
        state_path.write_text(json.dumps(state, indent=2) + '\n')
        print(json.dumps(result, indent=2))
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)


if __name__ == '__main__':
    main()
