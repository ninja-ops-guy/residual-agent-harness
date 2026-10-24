from __future__ import annotations

import unittest

from ai_providers import ProviderError
from ai_providers.adapters._http import map_http_error
from residual.core import ContractError
from residual.station.continuity import ContinuityProvider


class FakeProvider:
    def __init__(self, kind, placement, base_url, results, model=None):
        self.kind = kind
        self.name = kind
        self.model = model or kind + "-model"
        self.placement = placement
        self.profile = {"base_url": base_url}
        self.results = list(results)
        self.calls = 0

    def generate(self, packet, cap):
        self.calls += 1
        value = self.results.pop(0)
        if isinstance(value, Exception):
            raise value
        return value

    def wire_size(self, packet, cap):
        return 1


class ContinuityTests(unittest.TestCase):
    def test_structured_failure_classification(self):
        quota = map_http_error("openai", 429, b'{"error":{"code":"insufficient_quota"}}', {})
        self.assertEqual(quota.code, "quota_exhausted")
        self.assertTrue(quota.failover_allowed)
        self.assertFalse(quota.retryable)
        auth = map_http_error("openai", 401, b'{}', {})
        self.assertEqual(auth.code, "auth_rejected")
        self.assertTrue(auth.failover_allowed)
        policy = map_http_error("openai", 403, b'{"error":{"code":"quota_exhausted"}}', {})
        self.assertEqual(policy.code, "policy_denied")
        self.assertFalse(policy.failover_allowed)

    def test_arbitrary_text_cannot_authorize_quota(self):
        error = map_http_error("openai", 429, b"insufficient_quota", {})
        self.assertEqual(error.code, "rate_limit")
        self.assertTrue(error.retryable)
        self.assertTrue(error.failover_allowed)

    def test_whole_attempt_cross_placement_is_explicit(self):
        expected = object()
        remote = FakeProvider("openai", "remote", "https://api.example.test",
            [ProviderError(provider="openai", code="quota_exhausted", failover_allowed=True)])
        local = FakeProvider("ollama", "local", "http://127.0.0.1:11434", [expected])
        with self.assertRaises(ProviderError):
            ContinuityProvider([remote, local]).generate({}, 100, "cloud")
        remote.results = [ProviderError(provider="openai", code="quota_exhausted", failover_allowed=True)]
        chosen, reply = ContinuityProvider([remote, local], cross_placement=True).generate({}, 100, "cloud")
        self.assertIs(chosen, local)
        self.assertIs(reply, expected)

    def test_policy_denial_blocks_fallback(self):
        local = FakeProvider("ollama", "local", "http://127.0.0.1:11434",
            [ProviderError(provider="ollama", code="policy_denied", failover_allowed=False)])
        remote = FakeProvider("openai", "remote", "https://api.example.test", [object()])
        with self.assertRaises(ProviderError):
            ContinuityProvider([local, remote], cross_placement=True).generate({}, 100, "local")
        self.assertEqual(remote.calls, 0)

    def test_same_route_preferred_and_same_domain_rejected(self):
        local = FakeProvider("ollama", "local", "http://127.0.0.1:11434", [object()])
        remote = FakeProvider("openai", "remote", "https://api.example.test",
                              [AssertionError("remote should not run")])
        chosen, _ = ContinuityProvider([remote, local], cross_placement=True).generate({}, 100, "local")
        self.assertIs(chosen, local)
        with self.assertRaises(ContractError):
            ContinuityProvider([
                FakeProvider("ollama", "local", "http://127.0.0.1:11434", [object()], "a"),
                FakeProvider("ollama", "local", "http://127.0.0.1:11434", [object()], "b"),
            ])

    def test_before_attempt_runs_for_each_actual_attempt(self):
        events = []
        first = FakeProvider("one", "local", "http://127.0.0.1:1",
            [ProviderError(provider="router", code="connection", retryable=True)])
        second = FakeProvider("two", "local", "http://127.0.0.1:2", [object()])
        ContinuityProvider([first, second]).generate({}, 12, "local",
            before_attempt=lambda p, packet, cap: events.append((p.kind, cap)))
        self.assertEqual(events, [("one", 12), ("two", 12)])


if __name__ == "__main__":
    unittest.main()
