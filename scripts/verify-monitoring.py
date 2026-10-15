"""Exercise local monitoring with bounded read traffic, HPA observations, and real queries."""
import argparse
import base64
import json
import math
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from contextlib import ExitStack, contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--context', required=True)
    parser.add_argument('--namespace', default='stockflow-gitops-smoke')
    parser.add_argument('--duration', type=int, default=120)
    args = parser.parse_args()
    if args.context != 'kind-stockflow-smoke' or not args.namespace.endswith('-smoke'):
        parser.error('This automated experiment is restricted to the disposable local cluster')
    if not 30 <= args.duration <= 180:
        parser.error('Use 30..180 seconds of bounded traffic')
    kube = ['kubectl', '--context', args.context]
    (ROOT / '.logs').mkdir(exist_ok=True)

    def run(tail):
        return subprocess.check_output(kube + tail, text=True)

    def get(namespace, kind):
        return json.loads(run(['-n', namespace, 'get', kind, '-o', 'json']))

    @contextmanager
    def forward(namespace, service, port, target):
        with (ROOT / '.logs' / f'monitoring-forward-{port}.log').open('w') as log:
            process = subprocess.Popen(kube + ['-n', namespace, 'port-forward', '--address', '127.0.0.1', 'svc/' + service, f'{port}:{target}'], stdout=log, stderr=log)
            try:
                for _ in range(60):
                    if process.poll() is not None:
                        raise RuntimeError(f'Port-forward failed on {port}; check its log or a busy port')
                    try:
                        with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/health' if port == 3002 else f'http://127.0.0.1:{port}/health' if port == 3001 else f'http://127.0.0.1:{port}/-/ready', timeout=1):
                            break
                    except Exception:
                        time.sleep(1)
                else:
                    raise RuntimeError(f'Service on {port} did not become ready')
                yield
            finally:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)

    def request(url, headers=None):
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers or {}), timeout=15) as response:
            return json.load(response)

    def grafana_status():
        pods = get('monitoring', 'pods')['items']
        pod = next(pod for pod in pods if pod['metadata']['labels'].get('app.kubernetes.io/name') == 'grafana' and not pod['metadata'].get('deletionTimestamp'))
        return {'pod': pod['metadata']['name'], 'containers': [{'name': c['name'], 'ready': c['ready'], 'restarts': c['restartCount']} for c in pod['status']['containerStatuses']]}

    with ExitStack() as stack:
        stack.enter_context(forward(args.namespace, 'stockflow-stockflow-frontend', 3001, 80))
        stack.enter_context(forward('monitoring', 'monitoring-kube-prometheus-prometheus', 9090, 9090))
        stack.enter_context(forward('monitoring', 'monitoring-grafana', 3002, 80))
        before = grafana_status()
        hpa_samples = []
        began = time.monotonic()

        def sample():
            hpa = get(args.namespace, 'hpa/stockflow-stockflow-backend')['status']
            deployment = get(args.namespace, 'deployment/stockflow-stockflow-backend')['status']
            record = {'elapsed_seconds': round(time.monotonic() - began, 1), 'current_replicas': hpa.get('currentReplicas'), 'desired_replicas': hpa.get('desiredReplicas'), 'ready_replicas': deployment.get('readyReplicas', 0), 'cpu_utilization_percent': next((m.get('resource', {}).get('current', {}).get('averageUtilization') for m in hpa.get('currentMetrics', []) if m.get('resource', {}).get('name') == 'cpu'), None)}
            hpa_samples.append(record)
            (ROOT / '.logs/hpa-samples.json').write_text(json.dumps(hpa_samples, indent=2) + '\n')
            if len(hpa_samples) == 1 or record['current_replicas'] != hpa_samples[-2]['current_replicas']:
                print('HPA observation: ' + json.dumps(record), flush=True)
            return record

        sample()
        with (ROOT / '.logs/load-test-output.txt').open('w') as output:
            load = subprocess.Popen([sys.executable, str(ROOT / 'scripts/load-test.py'), '--base-url', 'http://127.0.0.1:3001', '--duration', str(args.duration), '--concurrency', '12', '--rps', '80', '--output', str(ROOT / '.logs/load-test.json')], stdout=output, stderr=output)
            try:
                while load.poll() is None:
                    sample()
                    time.sleep(5)
                if load.returncode:
                    raise RuntimeError('Bounded read load failed; inspect .logs/load-test-output.txt')
            finally:
                if load.poll() is None:
                    load.terminate()
                    load.wait(timeout=10)
        load_result = json.loads((ROOT / '.logs/load-test.json').read_text())
        dashboard = json.loads((ROOT / 'monitoring/stockflow.json').read_text())
        queries = []
        for panel in dashboard['panels']:
            expr = panel['targets'][0]['expr'].replace('$namespace', args.namespace).replace('$__rate_interval', '2m')
            result = request('http://127.0.0.1:9090/api/v1/query?' + urllib.parse.urlencode({'query': expr}))
            assert result['status'] == 'success', panel['title']
            values = result['data']['result']
            assert values and all(math.isfinite(float(item['value'][1])) for item in values), f'No finite live data for {panel["title"]}'
            queries.append({'panel': panel['title'], 'query': expr, 'series': len(values), 'values': [item['value'][1] for item in values]})
        targets = request('http://127.0.0.1:9090/api/v1/targets')['data']['activeTargets']
        targets = [target for target in targets if target['labels'].get('namespace') == args.namespace and target['labels'].get('service') == 'stockflow-stockflow-backend']
        assert len(targets) >= 2 and all(target['health'] == 'up' and not target['lastError'] for target in targets)
        credentials = get('monitoring', 'secret/monitoring-grafana')['data']
        username = base64.b64decode(credentials['admin-user']).decode()
        password = base64.b64decode(credentials['admin-password']).decode()
        headers = {'Authorization': 'Basic ' + base64.b64encode((username + ':' + password).encode()).decode()}
        grafana = request('http://127.0.0.1:3002/api/dashboards/uid/stockflow-overview', headers)
        assert len(grafana['dashboard']['panels']) == 6
        assert request('http://127.0.0.1:3002/api/datasources/uid/prometheus', headers)['type'] == 'prometheus'
        # Browser credentials travel through stdin and are never written to reports.
        browser = subprocess.run(['node', str(ROOT / 'scripts/capture-monitoring.mjs')], input=json.dumps({'username': username, 'password': password, 'namespace': args.namespace}), text=True, encoding='utf-8', errors='replace', capture_output=True)
        if browser.returncode:
            (ROOT / '.logs/grafana-browser-error.txt').write_text(browser.stderr.replace(password, '[redacted]'), encoding='utf-8')
            raise RuntimeError('Grafana browser capture failed; repeat capture after checking the UI')
        print(browser.stdout, end='', flush=True)
        # Observe the normal HPA stabilization window after traffic stops.
        for _ in range(40):
            if sample()['current_replicas'] == 2 and time.monotonic() - began > args.duration + 60:
                break
            time.sleep(5)
        after = grafana_status()
        assert before['pod'] == after['pod'] and before['containers'] == after['containers'] and all(c['ready'] for c in after['containers']), 'Grafana restarted during the experiment'
        result = {'verified_on': datetime.now(timezone(timedelta(hours=5, minutes=30))).date().isoformat(), 'environment': 'Local kind, not EKS', 'aws_deployed': False, 'namespace': args.namespace, 'load': load_result, 'prometheus_backend_targets_up': len(targets), 'dashboard_uid': 'stockflow-overview', 'dashboard_live_queries': queries, 'hpa_samples': hpa_samples, 'hpa_max_ready_replicas': max(item['ready_replicas'] for item in hpa_samples), 'hpa_scaled_above_two': any(item['ready_replicas'] > 2 for item in hpa_samples), 'grafana_containers_stable': after, 'screenshot': 'docs/screenshots/stockflow-grafana-local.png'}
        (ROOT / '.logs/observability-verification.json').write_text(json.dumps(result, indent=2) + '\n')
        print(f'PASS: six dashboard queries populated; {len(targets)} UP targets; HPA peak Ready replicas {result["hpa_max_ready_replicas"]}', flush=True)


if __name__ == '__main__':
    main()
