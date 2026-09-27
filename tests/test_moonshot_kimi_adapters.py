import contextlib
import io
import json
import socket
import threading
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from ai_providers import ChatRequest, Message, ProviderName, Role
from ai_providers.core import AuthenticationError, ProviderError
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

    def test_kimi_claw_accepts_only_openclaw_agent_targets(self):
        adapter = KimiClawAdapter(api_key="gateway-token")
        for model in ("openclaw", "openclaw/default", "openclaw/research", "openclaw:research", "agent:research"):
            with self.subTest(model=model):
                body = adapter._build_body(self.request(model))
                self.assertEqual(body["model"], model)
                self.assertTrue(adapter.supports_tools(model))
        for model in ("kimi-k3", "moonshot/kimi-k3", "openclaw/../../main", "random"):
            with self.subTest(model=model):
                with self.assertRaises(ProviderError):
                    adapter._build_body(self.request(model))
                self.assertFalse(adapter.supports_tools(model))
        with self.assertRaises(ContractError):
            normalize_profile({"kind": "kimi_claw", "model": "kimi-k3"}, "local")

    def test_kimi_claw_uses_gateway_specific_env_without_cloud_key_leakage(self):
        profile = normalize_profile({"kind": "kimi_claw", "model": "openclaw/default"}, "local")
        with patch.dict("os.environ", {"OPENCLAW_GATEWAY_TOKEN": "official-token", "LLM_API_KEY": "cloud-secret"}, clear=True):
            adapter = make_adapter(profile)
            self.assertEqual(adapter._headers()["Authorization"], "Bearer official-token")
        with patch.dict("os.environ", {"OPENCLAW_GATEWAY_PASSWORD": "official-password"}, clear=True):
            adapter = make_adapter(profile)
            self.assertEqual(adapter._headers()["Authorization"], "Bearer official-password")
        with patch.dict("os.environ", {"LLM_API_KEY": "cloud-secret"}, clear=True):
            adapter = make_adapter(profile)
            self.assertNotIn("Authorization", adapter._headers())

    def test_kimi_claw_conflicting_gateway_secrets_fail_closed(self):
        profile = normalize_profile({"kind": "kimi_claw", "model": "openclaw/default"}, "local")
        with patch.dict("os.environ", {
            "OPENCLAW_GATEWAY_TOKEN": "token-a",
            "OPENCLAW_GATEWAY_PASSWORD": "password-b",
        }, clear=True):
            with self.assertRaises(ProviderError) as ctx:
                make_adapter(profile)
            self.assertEqual(ctx.exception.provider, "kimi_claw")
            self.assertEqual(ctx.exception.code, "config")

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


class _FakeResponse:
    """Minimal context-manager response for injected openers."""

    def __init__(self, payload):
        self._raw = io.BytesIO(json.dumps(payload).encode())

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self, limit=-1):
        return self._raw.read(limit)


class _RecordingOpener:
    """Opener double that records each request and replies per Authorization."""

    def __init__(self, behavior=None):
        self.behavior = behavior
        self.requests = []
        self._lock = threading.Lock()

    def open(self, request, timeout=None):
        with self._lock:
            self.requests.append(request)
        if self.behavior is not None:
            raise self.behavior
        auth = request.headers.get("Authorization", "")
        payload = {
            "choices": [{"message": {"content": "echo:" + auth}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        }
        return _FakeResponse(payload)


@contextlib.contextmanager
def _loopback_server(response, status=200, body=None):
    captured = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            raw = self.rfile.read(int(self.headers["Content-Length"]))
            captured.append({"headers": dict(self.headers), "body": raw})
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            data = body if body is not None else json.dumps(response).encode()
            self.wfile.write(data)

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_port}/v1", captured
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)


class AdapterConformanceHardeningTests(unittest.TestCase):
    """Strengthening-only conformance: attribution, fail-closed transport,
    timeout propagation, and concurrent-session isolation."""

    def request(self, model):
        return ChatRequest(
            model=model,
            messages=(Message(Role.USER, "hello"),),
            max_tokens=64,
        )

    def adapters(self):
        return (
            (MoonshotAdapter(api_key="moonshot-secret"), "moonshot", "kimi-k3"),
            (KimiClawAdapter(api_key="claw-secret"), "kimi_claw", "openclaw/default"),
        )

    def test_exact_provider_attribution_on_transport_errors(self):
        for adapter, name, model in self.adapters():
            with self.subTest(provider=name):
                adapter.opener = _RecordingOpener(behavior=urllib.error.URLError("boom"))
                with self.assertRaises(ProviderError) as ctx:
                    adapter.chat(self.request(model))
                err = ctx.exception
                self.assertEqual(err.provider, name)
                self.assertEqual(err.code, "connection")
                self.assertTrue(err.retryable)

    def test_transport_errors_fail_closed_without_leaking_credentials(self):
        for adapter, name, model in self.adapters():
            with self.subTest(provider=name):
                adapter.opener = _RecordingOpener(behavior=OSError("connection reset"))
                with self.assertRaises(ProviderError) as ctx:
                    adapter.chat(self.request(model))
                self.assertEqual(ctx.exception.provider, name)
                self.assertNotIn("secret", str(ctx.exception))
                self.assertNotIn("secret", repr(ctx.exception.to_dict()))

    def test_timeout_propagates_as_retryable_timeout_error(self):
        for behavior in (socket.timeout("timed out"), TimeoutError("timed out")):
            for adapter, name, model in self.adapters():
                with self.subTest(provider=name, behavior=type(behavior).__name__):
                    adapter.opener = _RecordingOpener(behavior=behavior)
                    with self.assertRaises(ProviderError) as ctx:
                        adapter.chat(self.request(model))
                    err = ctx.exception
                    self.assertEqual(err.provider, name)
                    self.assertEqual(err.code, "timeout")
                    self.assertTrue(err.retryable)

    def test_invalid_timeout_config_fails_closed(self):
        for adapter, name, model in self.adapters():
            with self.subTest(provider=name):
                adapter.timeout = 0
                with self.assertRaises(ProviderError) as ctx:
                    adapter.chat(self.request(model))
                self.assertEqual(ctx.exception.provider, name)
                self.assertEqual(ctx.exception.code, "config")

    def test_http_401_fails_closed_without_echoing_response_body(self):
        secret_body = b'{"error": {"message": "bad key claw-secret leaked"}}'
        with _loopback_server({}, status=401, body=secret_body) as (base, _):
            adapter = KimiClawAdapter(api_key="claw-secret", base_url=base)
            with self.assertRaises(AuthenticationError) as ctx:
                adapter.chat(self.request("openclaw/default"))
            err = ctx.exception
            self.assertEqual(err.provider, "kimi_claw")
            self.assertEqual(err.code, "authentication")
            self.assertEqual(err.status, 401)
            self.assertFalse(err.retryable)
            self.assertNotIn("claw-secret", str(err))

    def test_redirects_are_refused_fail_closed(self):
        payload = {"choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}]}
        with _loopback_server(payload, status=302) as (base, _):
            adapter = KimiClawAdapter(api_key="claw-secret", base_url=base)
            with self.assertRaises(ProviderError) as ctx:
                adapter.chat(self.request("openclaw/default"))
            self.assertEqual(ctx.exception.provider, "kimi_claw")
            self.assertNotEqual(ctx.exception.code, "invalid_response")

    def test_concurrent_sessions_are_isolated(self):
        def run(adapter, model, results, index):
            try:
                resp = adapter.chat(self.request(model))
                results[index] = resp.content
            except Exception as exc:  # surfaced via assertion below
                results[index] = exc

        moon_a = MoonshotAdapter(api_key="moon-key-A")
        moon_b = MoonshotAdapter(api_key="moon-key-B")
        moon_a.opener = _RecordingOpener()
        moon_b.opener = _RecordingOpener()
        results = [None, None]
        threads = [
            threading.Thread(target=run, args=(moon_a, "kimi-k3", results, 0)),
            threading.Thread(target=run, args=(moon_b, "kimi-k3", results, 1)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
        for value in results:
            self.assertIsInstance(value, str)
        self.assertEqual(results[0], "echo:Bearer moon-key-A")
        self.assertEqual(results[1], "echo:Bearer moon-key-B")
        # Credentials stayed on their own session's wire request only.
        auths = [r.headers.get("Authorization") for r in moon_a.opener.requests]
        self.assertEqual(auths, ["Bearer moon-key-A"])
        auths = [r.headers.get("Authorization") for r in moon_b.opener.requests]
        self.assertEqual(auths, ["Bearer moon-key-B"])
        self.assertNotIn(b"moon-key-B", moon_a.wire_bytes(self.request("kimi-k3")))
        self.assertNotIn(b"moon-key-A", moon_b.wire_bytes(self.request("kimi-k3")))

    def test_concurrent_kimi_claw_sessions_over_real_loopback_http(self):
        payload = {"choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}]}
        with _loopback_server(payload) as (base, captured):
            adapters = (
                KimiClawAdapter(api_key="token-one", base_url=base),
                KimiClawAdapter(api_key="token-two", base_url=base),
            )
            errors = []

            def run(adapter):
                try:
                    for _ in range(5):
                        resp = adapter.chat(self.request("openclaw/default"))
                        assert resp.content == "ok"
                except Exception as exc:
                    errors.append(exc)

            threads = [threading.Thread(target=run, args=(a,)) for a in adapters]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=20)
            self.assertEqual(errors, [])
            auths = {c["headers"].get("Authorization") for c in captured}
            self.assertEqual(auths, {"Bearer token-one", "Bearer token-two"})
            for c in captured:
                self.assertNotIn("token-one", c["body"].decode())
                self.assertNotIn("token-two", c["body"].decode())


if __name__ == "__main__":
    unittest.main()
