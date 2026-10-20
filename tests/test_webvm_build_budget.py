"""Regression tests for browser and standalone build output-token bounds."""
from pathlib import Path
import tempfile
import unittest

from residual.core import ContractError
from residual.workbench.build import (
    MAX_BUILD_OUTPUT_TOKENS as STANDALONE_BUILD_OUTPUT_TOKENS,
    make_build_task,
)
from residual.workbench.conversation_build import (
    MAX_BUILD_OUTPUT_TOKENS as CONVERSATION_BUILD_OUTPUT_TOKENS,
    make_task,
)


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

    def standalone_request(self, tokens: int) -> dict:
        request = self.request(tokens)
        request.pop("conversation_id")
        return request

    def test_build_entry_points_accept_8192_output_tokens(self):
        self.assertEqual(CONVERSATION_BUILD_OUTPUT_TOKENS, 8192)
        self.assertEqual(STANDALONE_BUILD_OUTPUT_TOKENS, 8192)
        with tempfile.TemporaryDirectory() as folder:
            _, _, _, conversation_limits, _, _ = make_task(self.request(8192), Path(folder))
            _, _, _, standalone_limits = make_build_task(self.standalone_request(8192), Path(folder))
        self.assertEqual(conversation_limits.max_output_tokens, 8192)
        self.assertEqual(standalone_limits.max_output_tokens, 8192)

    def test_build_entry_points_reject_8193_output_tokens(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ContractError, "mission budget outside public workbench bounds"):
                make_task(self.request(8193), Path(folder))
            with self.assertRaisesRegex(ContractError, "mission budget outside public workbench bounds"):
                make_build_task(self.standalone_request(8193), Path(folder))


if __name__ == "__main__":
    unittest.main()
