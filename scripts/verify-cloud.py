"""Verify the actual StockFlow EKS demo and public ALB, with explicit destructive demo stages."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--context', required=True)
    parser.add_argument('--stage', choices=['baseline', 'release', 'rollback', 'recovery', 'storage'], required=True)
    parser.add_argument('--expected-sha', required=True)
    args = parser.parse_args()
    if args.context != 'stockflow-eks-sydney':
        parser.error('This verifier targets only the reviewed StockFlow EKS context')
    kube = ['kubectl', '--context', args.context]

    def run(tail):
        return subprocess.check_output(kube + tail, text=True, timeout=200)

    outputs = json.loads(subprocess.check_output(['terraform', '-chdir=' + str(ROOT / 'terraform'), 'output', '-json'], text=True))
    config = json.loads(run(['config', 'view', '--minify', '-o', 'json']))
    if outputs['region']['value'] != 'ap-southeast-2' or config['clusters'][0]['cluster']['server'] != outputs['cluster_endpoint']['value']:
        raise RuntimeError('Kubeconfig does not match the applied Sydney cluster')

    def get(kind, component=None):
        command = ['-n', 'stockflow', 'get', kind, '-o', 'json']
        if component:
            command += ['-l', 'app.kubernetes.io/instance=stockflow,app.kubernetes.io/component=' + component]
        value = json.loads(run(command))
        return value.get('items', value)

    app = json.loads(run(['-n', 'argocd', 'get', 'application', 'stockflow', '-o', 'json']))
    assert app['status']['sync']['status'] == 'Synced' and app['status']['health']['status'] == 'Healthy'
    assert any(r['kind'] == 'Job' and r.get('hookPhase') == 'Succeeded' for r in app['status']['operationState']['syncResult']['resources']), 'Migration hook must succeed'
    ingress = get('ingress')[0]
    hostname = ingress['status']['loadBalancer']['ingress'][0]['hostname']
    if not hostname.endswith('.ap-southeast-2.elb.amazonaws.com'):
        raise RuntimeError('Unexpected public ALB hostname')
    origin = 'http://' + hostname

    def api(path, data=None, expected=200):
        request = urllib.request.Request(origin + path, data=None if data is None else json.dumps(data).encode(), headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                status, body = response.status, response.read()
        except urllib.error.HTTPError as error:
            status, body = error.code, error.read()
        assert status == expected, (path, status, body.decode()[:200])
        return json.loads(body) if body else None

    for _ in range(60):
        try:
            with urllib.request.urlopen(origin, timeout=10) as response:
                assert response.status == 200 and 'StockFlow' in response.read().decode()
            api('/api/dashboard')
            break
        except (urllib.error.URLError, AssertionError):
            time.sleep(5)
    else:
        raise RuntimeError('Public frontend/API routing did not become healthy')
    for component in ['backend', 'frontend']:
        run(['-n', 'stockflow', 'rollout', 'status', 'deployment/stockflow-stockflow-' + component, '--timeout=180s'])
        deployment = get('deployments', component)[0]
        assert deployment['status'].get('readyReplicas', 0) >= 2
        assert deployment['spec']['template']['spec']['containers'][0]['image'].endswith(':' + args.expected_sha)
    pvc = get('pvc')[0]
    assert pvc['status']['phase'] == 'Bound' and pvc['spec']['storageClassName'] == 'gp3'
    state_path = ROOT / '.logs/cloud-runtime.json'
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    if args.stage == 'baseline':
        product = api('/api/products', {'sku': 'AWS-' + uuid.uuid4().hex[:8].upper(), 'name': 'AWS capstone inventory proof', 'unit_price': '49.99', 'category': 'Cloud demo'}, 201)
        path = f'/api/products/{product["id"]}'
        api(path + '/movements', {'movement_type': 'IN', 'quantity': 10}, 201)
        api(path + '/movements', {'movement_type': 'OUT', 'quantity': 3}, 201)
        api(path + '/movements', {'movement_type': 'OUT', 'quantity': 8}, 409)
        state = {'environment':'AWS EKS Sydney','origin':origin,'product_id':product['id'],'pvc_uid':pvc['metadata']['uid'],'volume_name':pvc['spec']['volumeName'],'stages':[]}
    assert state['origin'] == origin and state['pvc_uid'] == pvc['metadata']['uid']
    if args.stage in ['recovery','storage']:
        component = 'backend' if args.stage == 'recovery' else 'postgres'
        before = get('pods', component)
        previous = {pod['metadata']['uid'] for pod in before}
        run(['-n', 'stockflow', 'delete', 'pod', before[0]['metadata']['name'], '--wait=true', '--timeout=90s'])
        minimum = 2 if component == 'backend' else 1
        for _ in range(120):
            pods = get('pods', component)
            ready = [pod for pod in pods if not pod['metadata'].get('deletionTimestamp') and any(c['type']=='Ready' and c['status']=='True' for c in pod.get('status',{}).get('conditions',[]))]
            if len(ready) >= minimum and any(pod['metadata']['uid'] not in previous for pod in ready):
                break
            time.sleep(3)
        else:
            raise RuntimeError('Replacement demo Pod did not become Ready')
    for _ in range(45):
        try:
            assert api(f'/api/products/{state["product_id"]}')['quantity'] == 7
            break
        except (urllib.error.URLError, AssertionError):
            time.sleep(2)
    else:
        raise AssertionError('Retained cloud inventory did not recover')
    result = {'stage':args.stage,'verified_at_utc':datetime.now(timezone.utc).isoformat(),'git_revision':app['status']['sync']['revision'],'image_source_sha':args.expected_sha,'sync':'Synced','health':'Healthy','migration_hook':'Succeeded','quantity':7,'pvc_unchanged':True,'public_frontend_and_api':'pass','frontend_backend_ready_replicas':'at least 2'}
    state['stages'].append(result)
    state_path.write_text(json.dumps(state,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    print('Public StockFlow URL: ' + origin)


if __name__ == '__main__':
    main()
