"""Qualification for browser-local demo diagnostics; not execution evidence."""
from pathlib import Path
import shutil
import subprocess
import unittest


class WebVMDiagnosticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.diagnostics = (cls.root / 'demo/vm/mission-control-diagnostics.js').read_text(encoding='utf-8')
        cls.install = (cls.root / 'demo/vm/install_workbench.py').read_text(encoding='utf-8')

    def test_diagnostics_wrap_world_without_changing_authoritative_guest_modules(self):
        self.assertIn("from './mission-control-world.js'", self.diagnostics)
        self.assertIn("from './mission-control-diagnostics.js'", self.install)
        self.assertIn("'mission-control-diagnostics.js'", self.install)
        self.assertIn('authoritative_execution_evidence:false', self.diagnostics)

    def test_local_only_diagnostics_have_no_remote_analytics_transport(self):
        for forbidden in ('plausible.', 'google-analytics', 'analytics.google', 'segment.io', 'mixpanel.com'):
            self.assertNotIn(forbidden, self.diagnostics.lower())
        self.assertNotIn('sendBeacon(', self.diagnostics)

    def test_sensitive_payload_names_are_not_allowlisted(self):
        allowlist = self.diagnostics.split('const SAFE_CONTEXT_KEYS = new Set([', 1)[1].split(']);', 1)[0]
        for forbidden in ('prompt', 'content', 'authorization', 'cookie', 'api_key', 'token', 'messages', 'files'):
            self.assertNotIn(f"'{forbidden}'", allowlist)

    @unittest.skipUnless(shutil.which('node'), 'Node.js not installed')
    def test_javascript_diagnostic_contracts(self):
        completed = subprocess.run(
            ['node', '--experimental-default-type=module', '--test', 'tests/webvm-diagnostics.test.mjs'],
            cwd=self.root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=30,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout)


if __name__ == '__main__':
    unittest.main()
