import unittest

from ai_providers import ChatRequest, Message, ProviderName, Role
from ai_providers.adapters.kimi_claw_adapter import KimiClawAdapter
from ai_providers.adapters.moonshot_adapter import MoonshotAdapter
from ai_providers.registry import _default_registry
from residual.core import ContractError
from residual.modular import make_adapter, normalize_profile


class MoonshotAndKimiClawAdapterTests(unittest.TestCase):
    def request(self, model):
        return ChatRequest(
            model=model,
            messages=(Message(Role.USER, "hello"),),
            max_tokens=321,
        )

    def test_provider_names_are_closed_vocabulary(self):
        self.assertEqual(ProviderName("moonshot").value, "moonshot")
        self.assertEqual(ProviderName("kimi_claw").value, "kimi_claw")

    def test_moonshot_uses_distinct_identity_and_openai_wire_contract(self):
        adapter = MoonshotAdapter(api_key="test-secret")
        req = self.request("kimi-k3")
        body = adapter._build_body(req)
        self.assertEqual(adapter.name, "moonshot")
        self.assertEqual(adapter._request_url(req, False), "https://api.moonshot.ai/v1/chat/completions")
        self.assertEqual(body["model"], "kimi-k3")
        self.assertEqual(body["max_tokens"], 321)
        self.assertNotIn("max_completion_tokens", body)
        self.assertEqual(adapter._headers()["Authorization"], "Bearer test-secret")
        self.assertNotIn(b"test-secret", adapter.wire_bytes(req))
        self.assertTrue(adapter.supports_tools("kimi-k3"))
        self.assertFalse(adapter.supports_tools("other-model"))

    def test_kimi_claw_targets_openclaw_gateway_and_allows_stable_session(self):
        adapter = KimiClawAdapter(api_key="gateway-token")
        req = ChatRequest(
            model="openclaw/default",
            messages=(Message(Role.USER, "hello"),),
            max_tokens=222,
            extra={"user": "residual:mission-123"},
        )
        body = adapter._build_body(req)
        self.assertEqual(adapter.name, "kimi_claw")
        self.assertEqual(adapter._request_url(req, False), "http://127.0.0.1:18789/v1/chat/completions")
        self.assertEqual(body["model"], "openclaw/default")
        self.assertEqual(body["user"], "residual:mission-123")
        self.assertEqual(body["max_completion_tokens"], 222)
        self.assertEqual(adapter._headers()["Authorization"], "Bearer gateway-token")
        self.assertNotIn(b"gateway-token", adapter.wire_bytes(req))
        self.assertTrue(adapter.supports_tools("openclaw/default"))
        self.assertFalse(adapter.supports_tools("kimi-k3"))

    def test_moonshot_rejects_credential_redirection_to_compatible_host(self):
        for hostile in (
            "https://example.com/v1",
            "https://api.moonshot.ai.evil.example/v1",
            "http://api.moonshot.ai/v1",
            "https://api.moonshot.ai/other",
        ):
            with self.subTest(hostile=hostile):
                with self.assertRaises(Exception):
                    MoonshotAdapter(api_key="secret", base_url=hostile)
                with self.assertRaises(ContractError):
                    normalize_profile(
                        {"kind": "moonshot", "model": "kimi-k3", "base_url": hostile},
                        "remote",
                    )

    def test_kimi_claw_rejects_non_loopback_operator_token_destinations(self):
        for hostile in (
            "https://example.com/v1",
            "http://192.168.1.20:18789/v1",
            "http://127.0.0.1:18789/not-v1",
        ):
            with self.subTest(hostile=hostile):
                with self.assertRaises(Exception):
                    KimiClawAdapter(api_key="operator-secret", base_url=hostile)

        with self.assertRaises(ContractError):
            normalize_profile(
                {"kind": "kimi_claw", "model": "openclaw/default"},
                "remote",
            )

    def test_builtin_registry_exposes_both_adapters(self):
        names = _default_registry().names()
        self.assertIn("moonshot", names)
        self.assertIn("kimi_claw", names)

    def test_modular_runtime_profiles(self):
        moonshot = normalize_profile(
            {"kind": "moonshot", "model": "kimi-k3"},
            "remote",
        )
        self.assertEqual(moonshot["base_url"], "https://api.moonshot.ai/v1")
        self.assertIsInstance(make_adapter(moonshot, {"api_key": "x"}), MoonshotAdapter)

        claw = normalize_profile(
            {"kind": "kimi_claw", "model": "openclaw/default"},
            "local",
        )
        self.assertEqual(claw["base_url"], "http://127.0.0.1:18789/v1")
        self.assertIsInstance(make_adapter(claw, {"api_key": "x"}), KimiClawAdapter)

        with self.assertRaises(ContractError):
            normalize_profile({"kind": "moonshot", "model": "kimi-k3"}, "local")


if __name__ == "__main__":
    unittest.main()
