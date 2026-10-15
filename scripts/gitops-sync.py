"""Run an explicit ArgoCD sync through Kubernetes, with bounded health verification."""
import argparse
import json
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--context', required=True)
    parser.add_argument('--application', default='stockflow')
    parser.add_argument('--timeout', type=int, default=600)
    parser.add_argument('--enable-auto', action='store_true')
    parser.add_argument('--wait-only', action='store_true', help='Observe reconciliation without starting a sync')
    parser.add_argument('--revision', help='Require this Git commit before reporting success')
    args = parser.parse_args()
    if args.wait_only and not args.revision:
        parser.error('--wait-only requires --revision to avoid accepting stale health')
    kube = ['kubectl', '--context', args.context, '-n', 'argocd']

    def run(tail):
        return subprocess.check_output(kube + tail, text=True)

    def patch(data):
        # A temporary patch contains only Application settings, never credentials.
        (ROOT / '.logs').mkdir(exist_ok=True)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', dir=ROOT / '.logs', delete=False) as handle:
            json.dump(data, handle)
            path = Path(handle.name)
        try:
            run(['patch', 'application', args.application, '--type=merge', '--patch-file', str(path)])
        finally:
            path.unlink()

    initial = json.loads(run(['get', 'application', args.application, '-o', 'json']))
    if initial.get('operation') and not args.wait_only:
        raise SystemExit('An ArgoCD operation is already running; wait before starting another')
    # The apply strategy skips hooks, including the schema migration. Use hooks.
    if not args.wait_only:
        patch({'operation': {'initiatedBy': {'username': 'stockflow-runbook'}, 'retry': initial['spec'].get('syncPolicy', {}).get('retry', {}), 'sync': {'prune': True, 'syncStrategy': {'hook': {}}}}})
    deadline = time.monotonic() + args.timeout
    while time.monotonic() < deadline:
        app = json.loads(run(['get', 'application', args.application, '-o', 'json']))
        status = app.get('status', {})
        operation = status.get('operationState', {})
        if not app.get('operation') and operation.get('phase') in ['Failed', 'Error']:
            raise SystemExit('ArgoCD sync failed: ' + operation.get('message', 'inspect Application conditions'))
        if not app.get('operation') and operation.get('phase') == 'Succeeded' and status.get('sync', {}).get('status') == 'Synced' and status.get('health', {}).get('status') == 'Healthy' and (not args.revision or status['sync'].get('revision') == args.revision):
            break
        time.sleep(3)
    else:
        raise SystemExit('Timed out waiting for Synced/Healthy; inspect Application conditions and pod events')
    if args.enable_auto:
        patch({'spec': {'syncPolicy': {'automated': {'enabled': True, 'prune': True, 'selfHeal': True, 'allowEmpty': False}}}})
    result = {'application': args.application, 'context': args.context, 'sync': status['sync']['status'], 'health': status['health']['status'], 'revision': status['sync'].get('revision'), 'operation': operation['phase'], 'automated_enabled': args.enable_auto or initial['spec'].get('syncPolicy', {}).get('automated', {}).get('enabled', False)}
    print(json.dumps(result, indent=2))
    (ROOT / '.logs' / f'{args.application}-gitops.json').write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
