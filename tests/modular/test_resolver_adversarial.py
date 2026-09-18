"""MS-01 provider-resolver adversarial vectors (tests/design only).

Executable form of the vector tables in the wave-a A2 audit
(provider-resolution-adversarial.md), re-verified against main
(3cff6bcd52e352a6ba048c958949a7bbb2a039eb). No provider runtime behavior
is changed by this file.

Predicted gaps against the canonical resolver contract are expressed as
``unittest.expectedFailure`` tests asserting the *contract* behavior, so
they fail (as documented findings) until the resolver lands — they are
never weakened to green. Findings are enumerated in
docs/provider-resolver-migration.md (F-1..F-4).
"""
import os
import tempfile
import unittest
from unittest.mock import patch

from ai_providers import (
    DEFAULT_REGISTRY, ChatRequest, ChatResponse, Message, ModelRef,
    ProviderError, Registry, Role, Router, StreamChunk,
)
from ai_providers.core import ProviderName
from ai_providers.adapters._http import validate_url
from residual.core import ContractError, canonical, digest
from residual.modular import make_adapter, normalize_profile
from residual.quarantine import ProposedAction, QuarantineStore
from residual.station.models import save_settings
from residual.station.store import Store

REQ = ChatRequest("m", (Message(Role.USER, "hi"),))


def config_error(fn, *args, **kwargs):
    """Run fn and return the ProviderError it raised; fail if none/other."""
    try:
        fn(*args, **kwargs)
    except ProviderError as e:
        return e
    raise AssertionError("expected ProviderError")


# --- PR-01: exact-hostname spoofing / loopback bypass attempts ---------------
# Seam: ai_providers/adapters/_http.py validate_url (local hostname set is
# exactly {localhost, 127.0.0.1, ::1}; credentials/query/fragment/control
# chars rejected; plain http refused off-loopback).

HOSTNAME_SPOOF_VECTORS = [
    # (id, url, local, expect_reject, note)
    ("PR-01a", "http://localhost.evil.com:11434", True, True, "loopback suffix lookalike"),
    ("PR-01b", "http://127.0.0.1.evil.com", True, True, "dotted-quad suffix lookalike"),
    ("PR-01c", "http://2130706433/", True, True, "dword encoding of 127.0.0.1"),
    ("PR-01d", "http://[::1].evil.com/", True, True, "bracketed v6 lookalike"),
    ("PR-01e", "http://0x7f000001/", True, True, "hex encoding of 127.0.0.1"),
    ("PR-01f", "http://127.1/", True, True, "short-form loopback not in literal set"),
    ("PR-01g", "http://user:pw@127.0.0.1:11434", True, True, "embedded credentials"),
    ("PR-01h", "http://127.0.0.1:11434?x=1", True, True, "query string"),
    ("PR-01i", "http://127.0.0.1:11434/#frag", True, True, "fragment"),
    ("PR-01j", "http://127.0.0.1:11434/\npath", True, True, "control char < 33"),
    ("PR-01k", "http://example.com/", True, True, "plain http off-loopback"),
    ("PR-01l", "https://127.0.0.1:11434", True, False, "loopback https is in-policy"),
    ("PR-01m", "ftp://127.0.0.1/", True, True, "non-http(s) scheme"),
    ("PR-01n", "http://localhost:99999", True, True, "out-of-range port"),
    ("PR-01o", "http://example.com/", False, True, "http off-loopback refused even for remote routes"),
    ("PR-01p", "https://api.openai.com/v1", False, False, "https remote route accepted"),
    ("PR-01r", "http://localhost:11434", True, False, "loopback http accepted for local routes"),
]


class HostnameSpoofTests(unittest.TestCase):
    def test_vectors(self):
        for vid, url, local, reject, note in HOSTNAME_SPOOF_VECTORS:
            with self.subTest(vector=vid, note=note):
                if reject:
                    e = config_error(validate_url, url, "ollama", local=local)
                    self.assertEqual(e.code, "config", vid)
                else:
                    self.assertEqual(validate_url(url, "ollama", local=local), url.rstrip("/"), vid)


# --- PR-02: profile aliases & route confusion --------------------------------
# Seam: residual/modular.py normalize_profile; residual/station/models.py
# save_settings fallback/failover distinctness.

class ProfileAliasTests(unittest.TestCase):
    def test_local_route_requires_loopback_kind(self):  # PR-02a
        with self.assertRaisesRegex(ContractError, "Local routes require"):
            normalize_profile({"kind": "openai", "model": "gpt-x"}, "local")

    def test_local_ollama_rejects_cloud_models(self):  # PR-02b
        with self.assertRaisesRegex(ContractError, "cloud models belong"):
            normalize_profile({"kind": "ollama", "model": "qwen2.5:7b-cloud"}, "local")

    def test_local_openai_compatible_loopback_ok(self):  # PR-02c companion
        p = normalize_profile({"kind": "openai_compatible", "model": "registry:cloud-x",
                               "base_url": "http://localhost:8080/v1"}, "local")
        self.assertEqual(p["placement"], "local")

    def test_local_non_loopback_base_url_rejected(self):  # PR-02c
        with self.assertRaises(ContractError):
            normalize_profile({"kind": "openai_compatible", "model": "m",
                               "base_url": "https://registry.example.com"}, "local")

    def test_bedrock_region_injection_rejected(self):  # PR-02d
        with self.assertRaisesRegex(ContractError, "valid AWS region"):
            normalize_profile({"kind": "bedrock", "model": "m", "region": "us-east-1; rm -rf"}, "remote")

    def test_output_token_field_allowlist(self):  # PR-02e
        with self.assertRaisesRegex(ContractError, "Invalid output-limit field"):
            normalize_profile({"kind": "openai", "model": "m", "output_token_field": "num_predict"}, "remote")

    def test_model_control_char_rejected(self):  # PR-02f
        with self.assertRaises(ContractError):
            normalize_profile({"kind": "openai", "model": "m"}, "remote")

    def test_unknown_kind_rejected(self):  # PR-02g
        with self.assertRaisesRegex(ContractError, "supported provider"):
            normalize_profile({"kind": "not-a-provider", "model": "m"}, "remote")

    def test_f1_kind_host_not_pinned_current_behavior(self):  # PR-02h — finding F-1
        # Current main ACCEPTS a first-party kind with a foreign base_url:
        # normalize_profile does not pin provider kind to a canonical host.
        p = normalize_profile({"kind": "azure", "base_url": "https://api.openai.com/v1",
                               "model": "dep"}, "remote")
        self.assertEqual(p["base_url"], "https://api.openai.com/v1")

    @unittest.expectedFailure  # F-1: canonical resolver pins first-party kinds to canonical hosts
    def test_f1_canonical_contract_kind_host_pinned(self):
        with self.assertRaises(ContractError):
            normalize_profile({"kind": "azure", "base_url": "https://api.openai.com/v1",
                               "model": "dep"}, "remote")


class SettingsRouteConfusionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_duplicate_cloud_fallback_kind_rejected(self):  # PR-02i
        with self.assertRaisesRegex(ContractError, "distinct"):
            save_settings(self.store, {"cloud": {"kind": "openai", "model": "a"},
                                       "cloud_fallbacks": [{"kind": "openai", "model": "b"}]})

    def test_duplicate_local_failover_rejected(self):  # PR-02j
        with self.assertRaisesRegex(ContractError, "distinct"):
            save_settings(self.store, {"local_failover": ["m1", "m1"]})

    def test_local_failover_must_differ_from_primary(self):  # PR-02k
        primary = self.store.settings().get("local", {}).get("model")
        if not primary:
            save_settings(self.store, {"local": {"kind": "ollama", "model": "prim"}})
            primary = "prim"
        with self.assertRaisesRegex(ContractError, "differ from the primary"):
            save_settings(self.store, {"local_failover": [primary]})


# --- PR-03: credential-handle identity ----------------------------------------
# Seam: residual/station/models.py save_settings credential migration/clear;
# residual/modular.py make_adapter env fallback.

class CredentialHandleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def secrets(self):
        return self.store.settings().get("provider_credentials", {})

    def test_legacy_cloud_key_rebound_to_original_kind(self):  # PR-03a
        save_settings(self.store, {"cloud": {"kind": "openai", "model": "m"},
                                   "cloud_key": "K1"})
        save_settings(self.store, {"cloud": {"kind": "anthropic", "model": "m"}})
        creds = self.secrets()
        self.assertEqual(creds.get("openai", {}).get("api_key"), "K1")
        self.assertNotIn("api_key", creds.get("anthropic", {}))

    def test_per_kind_credentials_do_not_cross_bleed(self):  # PR-03b
        save_settings(self.store, {"provider_credentials": {"openai": {"api_key": "K1"}}})
        save_settings(self.store, {"provider_credentials": {"anthropic": {"api_key": "K2"}}})
        creds = self.secrets()
        self.assertEqual(creds["openai"]["api_key"], "K1")
        self.assertEqual(creds["anthropic"]["api_key"], "K2")

    def test_bedrock_api_key_field_rejected(self):  # PR-03d
        with self.assertRaisesRegex(ContractError, "Unsupported credential field"):
            save_settings(self.store, {"provider_credentials": {"bedrock": {"api_key": "x"}}})

    def test_credential_control_char_rejected(self):  # PR-03e
        with self.assertRaisesRegex(ContractError, "Invalid credential"):
            save_settings(self.store, {"provider_credentials": {"openai": {"api_key": "x"}}})

    def test_oversized_credential_rejected(self):  # PR-03f
        with self.assertRaisesRegex(ContractError, "Invalid credential"):
            save_settings(self.store, {"provider_credentials": {"openai": {"api_key": "A" * 10001}}})

    def test_unknown_setting_rejected(self):  # PR-03g
        with self.assertRaisesRegex(ContractError, "Unsupported setting"):
            save_settings(self.store, {"unknown_setting": 1})

    def test_unknown_credential_provider_rejected(self):  # PR-03h
        with self.assertRaisesRegex(ContractError, "Unknown credential provider"):
            save_settings(self.store, {"provider_credentials": {"evil": {"api_key": "x"}}})


class CredentialClearEnvFallbackTests(unittest.TestCase):
    """PR-03c / finding F-3: clearing the saved handle does not block the
    env-var fallback in make_adapter (residual/modular.py:44)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _profile(self):
        return normalize_profile({"kind": "openai", "model": "m"}, "remote")

    def test_current_behavior_cleared_key_resurrects_via_env(self):
        save_settings(self.store, {"provider_credentials": {"openai": {"api_key": "K1"}}})
        save_settings(self.store, {"provider_credentials": {"openai": {"clear": True}}})
        self.assertEqual(self.store.settings()["provider_credentials"].get("openai"), {})
        with patch.dict(os.environ, {"OPENAI_API_KEY": "ENV-KEY"}):
            adapter = make_adapter(self._profile(), {})
        self.assertEqual(adapter.api_key, "ENV-KEY")  # documented current behavior

    @unittest.expectedFailure  # F-3: canonical contract — clear means no credential from any source
    def test_canonical_contract_clear_blocks_env_fallback(self):
        save_settings(self.store, {"provider_credentials": {"openai": {"clear": True}}})
        with patch.dict(os.environ, {"OPENAI_API_KEY": "ENV-KEY"}):
            adapter = make_adapter(self._profile(), {})
        self.assertIsNone(adapter.api_key)


# --- PR-04: volatile-field exclusion & hash stability --------------------------
# Seams: residual/core.py canonical (sorted keys, allow_nan=False),
# residual/quarantine.py ProposedAction.fingerprint (identity hash excludes
# hold_id/timestamps), residual/station/models.py held provider_call args.

class HashStabilityTests(unittest.TestCase):
    def test_packet_digest_insertion_order_stable(self):  # PR-04a
        digests = {digest({"goal": "g", "files": {"b": "2", "a": "1"}}) for _ in range(3)}
        digests.add(digest({"files": {"a": "1", "b": "2"}, "goal": "g"}))
        self.assertEqual(len(digests), 1)

    def test_non_finite_json_rejected(self):  # PR-04b
        for bad in (float("inf"), float("-inf"), float("nan")):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    canonical({"x": bad})

    def test_fingerprint_excludes_hold_identity(self):  # PR-04c
        qs = QuarantineStore()
        args = {"packet_sha256": digest({"goal": "g"}), "candidates": ["ollama:m"]}
        a = ProposedAction("provider_call", "ollama", args, agent_id="worker")
        b = ProposedAction("provider_call", "ollama", dict(args), agent_id="worker")
        ha, hb = qs.hold(a), qs.hold(b)
        self.assertEqual(a.fingerprint, b.fingerprint)
        self.assertNotEqual(ha.hold_id, hb.hold_id)


# --- PR-05: model switching & segment boundaries -------------------------------
# Seams: ai_providers/router.py ModelRef.parse, Router._candidates (<=5,
# distinct), stream failover boundary (never append to an emitted prefix).

class ModelRefParsingTests(unittest.TestCase):
    def test_parse_vectors(self):
        cases = [
            ("PR-05c", "nosuchprovider:m", "unknown_provider"),
            ("PR-05d", "openai:", "unknown_provider"),
            ("PR-05e", ":m", "unknown_provider"),
            ("PR-05e2", "", "invalid_request"),
        ]
        for vid, raw, code in cases:
            with self.subTest(vector=vid):
                self.assertEqual(config_error(ModelRef.parse, raw).code, code)

    def test_bare_model_defaults_provider(self):  # PR-05g
        ref = ModelRef.parse("bare-model-no-colon")
        self.assertEqual(ref.provider, "default")
        self.assertEqual(ref.model, "bare-model-no-colon")


class _FakeProvider:
    def __init__(self, name, outcome):
        self.name, self.outcome, self.calls = name, outcome, 0

    def chat(self, req):
        self.calls += 1
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome

    def stream(self, req):
        self.calls += 1
        yield StreamChunk(content="prefix")
        raise ProviderError(provider=self.name, code="connection", retryable=True)


class RouterBoundaryTests(unittest.TestCase):
    def test_more_than_five_candidates_rejected(self):  # PR-05a
        r = Router(registry=Registry())
        with self.assertRaises(ProviderError) as ctx:
            r.chat("openai:gpt-4o", REQ,
                   ["anthropic:a", "google:g", "ollama:q", "azure:z", "bedrock:b"])
        self.assertEqual(ctx.exception.code, "invalid_request")

    def test_duplicate_candidates_rejected(self):  # PR-05b
        r = Router(registry=Registry())
        with self.assertRaises(ProviderError) as ctx:
            r.chat("openai:m", REQ, ["openai:m"])
        self.assertEqual(ctx.exception.code, "invalid_request")

    def test_router_name_parses_but_is_undispatchable(self):  # PR-05f — finding F-2
        # 'router' is admitted by ModelRef.parse (ProviderName.ROUTER) but no
        # factory is ever registered for it; failure is deferred to dispatch.
        ref = ModelRef.parse("router:m")
        self.assertEqual(ref.provider, "router")
        r = Router(registry=Registry())
        with self.assertRaises(ProviderError) as ctx:
            r.chat("router:m", REQ)
        self.assertEqual(ctx.exception.code, "unknown_provider")

    @unittest.expectedFailure  # F-2: canonical resolver rejects undispatchable names at parse time
    def test_canonical_contract_router_name_rejected_at_parse(self):
        with self.assertRaises(ProviderError):
            ModelRef.parse("router:m")

    def test_stream_failover_never_concatenates_emitted_prefix(self):  # PR-05h
        reg = Registry()
        one, two = _FakeProvider("openai", None), _FakeProvider("anthropic", None)
        reg.register("openai", lambda: one)
        reg.register("anthropic", lambda: two)
        stream = Router(registry=reg).stream("openai:x", REQ, ["anthropic:y"])
        self.assertEqual(next(stream).content, "prefix")
        with self.assertRaises(ProviderError) as ctx:
            next(stream)
        self.assertEqual(ctx.exception.code, "connection")
        self.assertEqual(two.calls, 0)  # no mid-stream model switch

    def test_generator_close_marks_stream_incomplete(self):  # PR-05i
        reg = Registry()
        one = _FakeProvider("openai", None)
        reg.register("openai", lambda: one)
        receipts = []
        stream = Router(registry=reg, after_attempt=receipts.append).stream("openai:x", REQ)
        next(stream)
        stream.close()
        self.assertEqual(receipts[-1]["status"], "failed")
        self.assertEqual(receipts[-1]["error"]["code"], "stream_incomplete")


# --- PR-06: unknown providers & registration guards ----------------------------
# Seam: ai_providers/registry.py lazy construction, closed vocabulary,
# factory name-mismatch -> config error.

class RegistryGuardTests(unittest.TestCase):
    def test_unregistered_provider_unknown(self):  # PR-06a
        with self.assertRaises(ProviderError) as ctx:
            Registry().get("openai")
        self.assertEqual(ctx.exception.code, "unknown_provider")

    def test_factory_name_mismatch_is_config_error(self):  # PR-06b
        reg = Registry()
        reg.register("openai", lambda: _FakeProvider("anthropic", None))
        with self.assertRaises(ProviderError) as ctx:
            reg.get("openai")
        self.assertEqual(ctx.exception.code, "config")

    def test_closed_vocabulary_at_registration(self):  # PR-06c
        with self.assertRaises(ValueError):
            Registry().register("bogus", lambda: None)

    def test_router_name_in_vocabulary_but_unregistered(self):  # F-2 corroboration
        self.assertIn("router", {v.value for v in ProviderName})
        self.assertNotIn("router", DEFAULT_REGISTRY.names())


if __name__ == "__main__":
    unittest.main()
