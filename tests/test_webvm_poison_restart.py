from __future__ import annotations

from pathlib import Path
import unittest


class WebVMPoisonRestartContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.install = (cls.root / 'demo/vm/install_workbench.py').read_text(encoding='utf-8')
        cls.mission = (cls.root / 'demo/vm/mission-control.js').read_text(encoding='utf-8')
        cls.patch = (cls.root / 'demo/vm/patch_webvm.py').read_text(encoding='utf-8')
        cls.qualify = (cls.root / 'demo/vm/qualify_webvm.py').read_text(encoding='utf-8')
        cls.smoke = (cls.root / 'demo/vm/provider_failure_smoke.py').read_text(encoding='utf-8')

    def test_poison_is_exposed_as_failed_health_not_starting_forever(self):
        self.assertIn('health: () => residualWorkerPoisoned ? "poisoned"', self.install)
        self.assertIn('VM WORKER POISONED · RESTART REQUIRED', self.install)
        self.assertIn('GUEST FAILED · RESTART REQUIRED', self.mission)
        self.assertIn('id="mc-restart"', self.mission)
        self.assertIn("health==='poisoned'", self.mission)

    def test_restart_rotates_overlay_instead_of_unpoisoning_current_guest(self):
        self.assertIn('residual.guest.generation.v1', self.patch)
        self.assertIn('function residualRestartGuest()', self.patch)
        self.assertIn('sessionStorage.setItem(residualGuestGenerationKey, next)', self.patch)
        self.assertIn('location.reload()', self.patch)
        self.assertIn('restart: () => residualRestartGuest()', self.install)
        self.assertIn('+ "-g-" + residualGuestGeneration()', self.qualify)
        # The host wiring may observe the poison path and recovery may create it,
        # but the restart path itself must not erase the durable fence in place.
        restart_body = self.patch.split('function residualRestartGuest()', 1)[1].split('function residualDecode64url', 1)[0]
        self.assertNotIn('unlink', restart_body)
        self.assertNotIn('removeItem', restart_body)
        self.assertNotIn('residual-workbench.poison', restart_body)

    def test_restart_is_blocked_during_active_work_and_ends_provider_session(self):
        self.assertIn("if (active || running || typeof host.restart !== 'function') return", self.mission)
        self.assertIn("provider.end(); $('restart').disabled = true", self.mission)
        self.assertIn("$('run').disabled=!ready||!!active||running", self.mission)

    def test_real_browser_acceptance_reproduces_poison_then_runs_real_audit(self):
        self.assertIn("printf \"RESIDUAL_WORKER_%s\\\\n\" POISONED", self.smoke)
        self.assertIn("test ! -e /tmp/residual-workbench.poison", self.smoke)
        self.assertIn("sessionStorage.getItem('residual.guest.generation.v1')", self.smoke)
        self.assertIn('PASS_FRESH_OVERLAY_AND_REAL_AUDIT_AFTER_EXPLICIT_RESTART', self.smoke)
        self.assertIn("select_option('audit')", self.smoke)
        self.assertIn("document.querySelector('#mc-verdict').textContent.startsWith('PASSED')", self.smoke)


if __name__ == '__main__':
    unittest.main()
