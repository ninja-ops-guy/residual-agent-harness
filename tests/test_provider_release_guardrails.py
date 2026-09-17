"""Source-level pins for release-critical provider/browser acceptance boundaries."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ProviderReleaseGuardrailTests(unittest.TestCase):
    def test_agent_policy_exists_and_requires_real_sdk_gate(self):
        agents = (ROOT / "AGENTS.md").read_text()
        policy = (ROOT / "docs/release/DEMO_REGRESSION_GUARDRAILS.md").read_text()
        self.assertIn("real Puter SDK", agents)
        self.assertIn("real Puter SDK", policy)
        self.assertIn("Narrow Chromium is not physical iOS/WebKit qualification", agents)

    def test_pages_deploy_runs_real_sdk_acceptance_after_deploy(self):
        workflow = (ROOT / ".github/workflows/pages.yml").read_text()
        deploy = workflow.index("uses: actions/deploy-pages@v4")
        sdk_gate = workflow.index("Verify published provider can load real Puter SDK")
        self.assertGreater(sdk_gate, deploy)
        self.assertIn("provider_sdk_smoke.py", workflow[sdk_gate:])
        self.assertIn("live-provider-evidence", workflow[sdk_gate:])

    def test_real_sdk_smoke_cannot_authenticate_or_infer(self):
        smoke = (ROOT / "demo/vm/provider_sdk_smoke.py").read_text()
        self.assertIn("js.puter.com", smoke)
        self.assertIn('"authentication": "NOT_RUN"', smoke)
        self.assertIn('"inference": "NOT_RUN"', smoke)
        self.assertNotIn("auth.signIn(", smoke)
        self.assertNotIn("ai.chat(", smoke)
        self.assertNotIn("ai.listModels(", smoke)
        self.assertNotIn("page.route(", smoke)


if __name__ == "__main__":
    unittest.main()
