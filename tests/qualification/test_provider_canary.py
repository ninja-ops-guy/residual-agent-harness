from __future__ import annotations

import hashlib
import unittest
from pathlib import Path

import scripts.qualification_provider_canary as canary


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = (ROOT / ".github" / "workflows" / "qualification-provider-canary.yml").read_text(encoding="utf-8")


class ProviderCanaryQualificationTests(unittest.TestCase):
    def test_canary_requires_exact_normalized_response(self):
        self.assertTrue(canary.exact_canary_match("  RESIDUAL_CANARY_OK\n"))
        self.assertFalse(canary.exact_canary_match("prefix RESIDUAL_CANARY_OK"))
        self.assertFalse(canary.exact_canary_match("RESIDUAL_CANARY_OK suffix"))

    def test_retained_error_redacts_known_secret_and_base_url(self):
        key = "super-secret-api-key"
        base_url = "https://user:pass@example.invalid/v1?token=signed-value"
        raw = f"request failed key={key} url={base_url}"
        reason, digest = canary.redact_error(RuntimeError(raw), secrets=(key, base_url))
        self.assertNotIn(key, reason)
        self.assertNotIn(base_url, reason)
        self.assertIn("<redacted>", reason)
        self.assertEqual(digest, hashlib.sha256(raw.encode("utf-8")).hexdigest())

    def test_workflow_passes_dispatch_strings_through_environment(self):
        self.assertIn("QUAL_MODEL: ${{ inputs.model }}", WORKFLOW)
        self.assertIn("QUAL_BASE_URL: ${{ inputs.base_url }}", WORKFLOW)
        self.assertIn('--model "$QUAL_MODEL"', WORKFLOW)
        self.assertIn('args+=(--base-url "$QUAL_BASE_URL")', WORKFLOW)
        self.assertNotIn("--model '${{ inputs.model }}'", WORKFLOW)
        self.assertNotIn("--base-url '${{ inputs.base_url }}'", WORKFLOW)


if __name__ == "__main__":
    unittest.main()
