"""Regression tests for browser build output-token bounds."""
from pathlib import Path
import tempfile
import unittest

from residual.core import ContractError
from residual.workbench.conversation_build import MAX_BUILD_OUTPUT_TOKENS, make_task


class BrowserBuildBudgetTests(unittest.TestCase):
    def request(self, tokens: int) -> dict:
        return {
            "id": "m-" + "a" * 32,
            "conversation_id": "c-" + "b" * 32,
            "mode": "build",
            "prompt": "Build a calculator",
            "files": [],
            "model": "openai/gpt-5.4-nano",
            "max_calls": 2,
            "max_output_tokens": tokens,
            "cloud_consent": True,
            "required_text": [],
        }

    def test_build_accepts_8192_output_tokens(self):
        self.assertEqual(MAX_BUILD_OUTPUT_TOKENS, 8192)
        with tempfile.TemporaryDirectory() as folder:
            _, _, _, limits, _, _ = make_task(self.request(8192), Path(folder))
        self.assertEqual(limits.max_output_tokens, 8192)

    def test_build_rejects_8193_output_tokens(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ContractError, "mission budget outside public workbench bounds"):
                make_task(self.request(8193), Path(folder))


if __name__ == "__main__":
    unittest.main()
