from __future__ import annotations

import os
import unittest
from unittest import mock

from scripts.qualification_provider_guard import (
    allowed_custom_base_urls,
    require_allowed_credential_destination,
)


class ProviderDestinationGuardTests(unittest.TestCase):
    def test_custom_credential_destination_must_be_https_and_allowlisted(self):
        allowed = "https://gateway.example/v1,https://other.example"
        self.assertEqual(
            require_allowed_credential_destination(
                "openai_compatible", "https://gateway.example/v1/", allowlist=allowed
            ),
            "https://gateway.example/v1",
        )
        with self.assertRaises(ValueError):
            require_allowed_credential_destination(
                "openai_compatible", "https://evil.example/v1", allowlist=allowed
            )
        with self.assertRaises(ValueError):
            require_allowed_credential_destination(
                "openai_compatible", "http://gateway.example/v1", allowlist=allowed
            )

    def test_credentials_in_custom_url_are_rejected_even_when_host_is_allowlisted(self):
        with self.assertRaises(ValueError):
            require_allowed_credential_destination(
                "openai", "https://user:pass@gateway.example/v1",
                allowlist="https://gateway.example/v1",
            )

    def test_builtin_provider_default_needs_no_custom_allowlist(self):
        self.assertIsNone(require_allowed_credential_destination("openai", None, allowlist=""))

    def test_ollama_is_outside_credential_destination_guard(self):
        self.assertEqual(
            require_allowed_credential_destination("ollama", "http://127.0.0.1:11434", allowlist=""),
            "http://127.0.0.1:11434",
        )

    def test_environment_allowlist_is_parsed_exactly(self):
        with mock.patch.dict(os.environ, {
            "RESIDUAL_QUALIFICATION_ALLOWED_BASE_URLS":
                "https://one.example/v1\nhttps://two.example/v1,"
        }):
            self.assertEqual(
                allowed_custom_base_urls(),
                frozenset({"https://one.example/v1", "https://two.example/v1"}),
            )


if __name__ == "__main__":
    unittest.main()
