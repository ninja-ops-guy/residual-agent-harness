"""Static deployment wiring regressions, not a substitute for guest proof."""
from __future__ import annotations

import os
import re
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / '.github/workflows/pages.yml').read_text()


def step(name: str) -> str:
    marker = '      - name: ' + name + '\n'
    assert WORKFLOW.count(marker) == 1, f'missing/duplicated workflow step {name}'
    return WORKFLOW.split(marker, 1)[1].split('      - ', 1)[0]


class DeploymentWorkflowTests(unittest.TestCase):
    def test_build_emits_artifact_identity(self):
        build = WORKFLOW.split('  deploy:\n', 1)[0]
        self.assertIn('pages-artifact-name: ${{ steps.pages-artifact.outputs.name }}', build)
        self.assertIn('id: pages-artifact', step('Record attempt-specific Pages artifact name'))

    def test_rebuilt_attempts_have_distinct_names(self):
        script = textwrap.dedent(step('Record attempt-specific Pages artifact name').split('        run: |\n', 1)[1])
        values = []
        with tempfile.TemporaryDirectory() as folder:
            for attempt in (1, 2):
                output = Path(folder) / str(attempt)
                env = dict(os.environ, GITHUB_RUN_ID='123456', GITHUB_RUN_ATTEMPT=str(attempt), GITHUB_OUTPUT=str(output))
                subprocess.run(['bash', '-euo', 'pipefail', '-c', script], env=env, check=True, timeout=5)
                values.append(output.read_text().strip())
        self.assertEqual(values, ['name=github-pages-123456-1', 'name=github-pages-123456-2'])

    def test_upload_selects_build_name(self):
        self.assertIn('name: ${{ steps.pages-artifact.outputs.name }}', step('Upload only browser-qualified Pages artifact'))

    def test_deploy_only_retry_uses_original_build_output(self):
        deploy = step('Deploy')
        self.assertIn('artifact_name: ${{ needs.build-and-browser-proof.outputs.pages-artifact-name }}', deploy)
        self.assertNotIn('github.run_attempt', deploy)
        self.assertNotIn('github-pages\n', deploy)

    def test_real_browser_failure_blocks_upload(self):
        proof = step('Prove actual generated artifact in desktop and narrow browsers')
        self.assertIn('set -euo pipefail', proof)
        self.assertIn('--output browser-evidence/desktop', proof)
        self.assertIn('--output browser-evidence/narrow --mobile', proof)
        self.assertNotIn('continue-on-error', WORKFLOW)
        self.assertLess(WORKFLOW.index('name: Prove actual generated artifact'), WORKFLOW.index('name: Upload only browser-qualified'))

    def test_publication_is_main_only_and_depends_on_browser_proof(self):
        deploy = WORKFLOW.split('  deploy:\n', 1)[1]
        self.assertIn("if: github.event_name != 'pull_request' && github.ref == 'refs/heads/main'", deploy)
        self.assertIn('needs: build-and-browser-proof', deploy)
        build = WORKFLOW.split('  deploy:\n', 1)[0]
        self.assertNotIn('pages: write', build)
        self.assertNotIn('id-token: write', build)

    def test_settings_preflight_precedes_publication(self):
        self.assertIn('--pages-config pages-config.json', step('Require GitHub Actions publishing source'))
        self.assertLess(WORKFLOW.index('name: Require GitHub Actions publishing source'), WORKFLOW.index('      - name: Deploy\n'))

    def test_both_live_viewports_bind_exact_revision(self):
        for name, output in (('Verify published WebVM revision and real guest execution', 'desktop'),
                             ('Verify published WebVM on narrow Chromium viewport', 'narrow')):
            with self.subTest(name=name):
                command = step(name)
                self.assertIn('--expected-sha "$GITHUB_SHA"', command)
                self.assertIn('${PAGE_URL%/}/demo/', command)
                self.assertIn('live-browser-evidence/' + output, command)
        self.assertIn('--mobile', step('Verify published WebVM on narrow Chromium viewport'))

    def test_failure_evidence_is_retained(self):
        for name in ('Retain browser proof and build identity', 'Retain live acceptance proof'):
            with self.subTest(name=name):
                self.assertIn('if: always()', step(name))
                self.assertIn('${{ github.run_id }}-${{ github.run_attempt }}', step(name))

    def test_core_and_cli_changes_requalify_demo(self):
        push, pr = WORKFLOW.split('  pull_request:\n')
        for section in (push, pr.split('  workflow_dispatch:', 1)[0]):
            self.assertIn("- 'residual/**'", section)
            self.assertIn("- 'pyproject.toml'", section)
            self.assertIn("- 'tests/test_webvm_*.py'", section)
        self.assertIn('tests.test_webvm_cli_output', step('Test publication contracts'))
        self.assertIn('tests.test_webvm_deployment_workflow', step('Test publication contracts'))


if __name__ == '__main__':
    unittest.main()
