"""Collect real read-only cluster output and run the isolated walkthrough recorder.

Records the existing dashboard and catalog without modifying inventory. Never
replaces Pods, changes infrastructure, or publishes credentials. Admin forwards
bind localhost.
"""
import base64
from contextlib import ExitStack, contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.request

from live_command_viewer import viewer

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / '.logs/walkthrough'
KUBE = ['kubectl', '--context', 'stockflow-eks-sydney', '--request-timeout=30s']


def run(command):
    return subprocess.check_output(command, text=True, encoding='utf-8', timeout=60)


@contextmanager
def forward(namespace, service, port, target):
    with (WORK / f'forward-{port}.log').open('w') as log:
        process = subprocess.Popen(KUBE + ['-n', namespace, 'port-forward', '--address', '127.0.0.1', 'svc/' + service, f'{port}:{target}'], stdout=log, stderr=log)
        try:
            time.sleep(3)
            if process.poll() is not None:
                raise RuntimeError(f'Cannot start port-forward {port}; inspect its private log')
            yield
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    os.environ['KUBECONFIG'] = str(ROOT / '.logs/eks.kubeconfig')
    commands = {
        'pods': KUBE + ['-n', 'stockflow', 'get', 'pods', '-o', 'wide'],
        'services': KUBE + ['-n', 'stockflow', 'get', 'svc,ingress'],
        'storage': KUBE + ['-n', 'stockflow', 'get', 'pvc,hpa'],
        'argocd': KUBE + ['-n', 'argocd', 'get', 'application', 'stockflow'],
        'nodes': KUBE + ['get', 'nodes'],
        'helm': ['helm', '--kube-context', 'stockflow-eks-sydney', 'list', '-A'],
        'git': ['git', 'log', '-12', '--format=%h %s'],
        'compose': ['docker', 'compose', 'ps'],
    }
    evidence = {'captured_at_utc': datetime.now(timezone.utc).isoformat(), 'commands': {}}
    for key, command in commands.items():
        output = run(command)
        evidence['commands'][key] = {'command': ' '.join(command), 'output': output}
        (WORK / f'{key}.txt').write_text(output, encoding='utf-8')
    pods = json.loads(run(KUBE + ['-n', 'stockflow', 'get', 'pods', '-o', 'json']))['items']
    assert len(pods) >= 5 and all(p['status']['phase'] == 'Running' and all(c['ready'] for c in p['status']['containerStatuses']) for p in pods)
    app = json.loads(run(KUBE + ['-n', 'argocd', 'get', 'application', 'stockflow', '-o', 'json']))
    assert app['status']['health']['status'] == 'Healthy' and app['status']['sync']['status'] == 'Synced'
    evidence['argocd_revision'] = app['status']['sync']['revision']
    deployments = json.loads(run(KUBE + ['-n', 'stockflow', 'get', 'deployments', '-o', 'json']))['items']
    evidence['images'] = sorted({c['image'] for d in deployments for c in d['spec']['template']['spec']['containers']})
    (WORK / 'commands.json').write_text(json.dumps(evidence, indent=2) + '\n')
    with ExitStack() as stack:
        viewer_origin = stack.enter_context(viewer())
        stack.enter_context(forward('stockflow', 'stockflow-stockflow-backend', 8001, 8000))
        stack.enter_context(forward('monitoring', 'monitoring-kube-prometheus-prometheus', 9090, 9090))
        stack.enter_context(forward('monitoring', 'monitoring-grafana', 3002, 80))
        stack.enter_context(forward('argocd', 'argocd-server', 8443, 443))
        def secret(namespace, name):
            return json.loads(run(KUBE + ['-n', namespace, 'get', 'secret', name, '-o', 'json']))['data']
        grafana = secret('monitoring', 'monitoring-grafana')
        argo = secret('argocd', 'argocd-initial-admin-secret')
        settings = {'grafana_user': base64.b64decode(grafana['admin-user']).decode(), 'grafana_password': base64.b64decode(grafana['admin-password']).decode(), 'argocd_password': base64.b64decode(argo['password']).decode(), 'viewer_origin': viewer_origin}
        # Only the child stdin receives credentials; no command-line or report copies.
        result = subprocess.run(['node', str(ROOT / 'scripts/record-walkthrough.mjs')], input=json.dumps(settings), text=True, encoding='utf-8', capture_output=True, timeout=1200)
        if result.returncode:
            message = result.stderr
            for value in settings.values():
                message = message.replace(value, '[redacted]')
            (WORK / 'recorder-error.txt').write_text(message, encoding='utf-8')
            raise RuntimeError('Walkthrough recording failed; inspect the private recorder-error.txt')
        print(result.stdout)
        subprocess.run(['docker', 'compose', '-f', 'compose.ci.yml', 'down'], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)


if __name__ == '__main__':
    main()
