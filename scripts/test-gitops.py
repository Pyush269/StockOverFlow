"""Verify the release and ArgoCD contract before touching a cluster."""
import re
import subprocess
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


class GitOpsTests(unittest.TestCase):
    def test_application_boundaries_and_hpa_ownership(self):
        for name, namespace, profile in [('application.yaml', 'stockflow', 'values-prod.yaml'), ('application-local.yaml', 'stockflow-gitops-smoke', 'values-local.yaml')]:
            app = yaml.safe_load((ROOT / 'argocd' / name).read_text())['spec']
            self.assertEqual(app['project'], 'stockflow')
            self.assertEqual(app['source']['repoURL'], 'https://github.com/Pyush269/StockOverFlow.git')
            self.assertEqual(app['source']['helm']['valueFiles'], [profile, 'values-release.yaml'])
            self.assertEqual(app['destination']['namespace'], namespace)
            self.assertNotIn('automated', app['syncPolicy'])
            self.assertIn('RespectIgnoreDifferences=true', app['syncPolicy']['syncOptions'])
            self.assertIn('FailOnSharedResource=true', app['syncPolicy']['syncOptions'])
            self.assertEqual(app['ignoreDifferences'][0]['jsonPointers'], ['/spec/replicas'])
            rendered = subprocess.check_output(['helm', 'template', 'stockflow', str(ROOT / 'helm/stockflow'), '-n', namespace, '-f', str(ROOT / 'helm/stockflow' / profile), '-f', str(ROOT / 'helm/stockflow/values-release.yaml')], text=True)
            objects = list(yaml.safe_load_all(rendered))
            backend = next(obj for obj in objects if obj and obj['kind'] == 'Deployment' and obj['metadata']['name'].endswith('-backend'))
            self.assertEqual(backend['metadata']['name'], app['ignoreDifferences'][0]['name'])
            self.assertNotIn('replicas', backend['spec'])

    def test_release_sha_consistency_and_no_secrets(self):
        release = yaml.safe_load((ROOT / 'helm/stockflow/values-release.yaml').read_text())
        sha = release['backend']['image']['tag']
        self.assertRegex(sha, r'^[a-f0-9]{40}$')
        self.assertEqual(sha, release['frontend']['image']['tag'])
        project = yaml.safe_load((ROOT / 'argocd/project.yaml').read_text())['spec']
        self.assertEqual(project['clusterResourceWhitelist'], [])
        self.assertFalse(any(kind['kind'] in ['Secret', '*'] for kind in project['namespaceResourceWhitelist']))
        self.assertEqual(len(project['sourceRepos']), 1)
        workflow = yaml.safe_load((ROOT / '.github/workflows/ci.yml').read_text())
        triggers = workflow.get('on', workflow.get(True))
        for event in ['push', 'pull_request']:
            self.assertIn('helm/**', triggers[event]['paths-ignore'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
