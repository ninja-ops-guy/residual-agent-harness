import contextlib
import io
import json
import socket
import threading
import unittest
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from ai_providers import ChatRequest, Message, ProviderName, Role
from ai_providers.core import AuthenticationError, ProviderError
from ai_providers.adapters.kimi_claw_adapter import KimiClawAdapter
from ai_providers.adapters.moonshot_adapter import MoonshotAdapter
from ai_providers.registry import _default_registry


class _RecordingOpener:
    """Opener that records requests and replays a scripted response."""

    def __init__(self, responder):
        self.responder = responder
        self.requests = []

    def open(self, request, timeout=None):
        body = request.data.decode() if request.data else None
        self.requests.append((request, body, timeout))
        return self.responder(request, body)


class AdapterConformanceHardeningTests(unittest.TestCase):
    def test_transport_error_attribution_and_fail_closed(self):
        def refuse(request, body):
            raise urllib.error.URLError("connection refused by peer")

        opener = _RecordingOpener(refuse)
        adapter = MoonshotAdapter(api_key="sk-test-secret-1", opener=opener)
        request = ChatRequest(messages=[Message(role=Role.USER, content="hi")], model="kimi-k2")
        with self.assertRaises(ProviderError) as caught:
            adapter.chat(request)
        err = caught.exception
        self.assertEqual(err.provider, "moonshot")
        self.assertEqual(err.code, "connection")
        self.assertTrue(err.retryable)
        self.assertNotIn("sk-test-secret-1", str(err))
        self.assertNotIn("sk-test-secret-1", repr(err.__dict__))

    def test_transport_error_attribution_kimi_claw(self):
        def refuse(request, body):
            raise urllib.error.URLError("connection refused by peer")

        opener = _RecordingOpener(refuse)
        adapter = KimiClawAdapter(token="claw-secret-2", opener=opener)
        request = ChatRequest(messages=[Message(role=Role.USER, content="hi")], model="kimi-claw")
        with self.assertRaises(ProviderError) as caught:
            adapter.chat(request)
        err = caught.exception
        self.assertEqual(err.provider, "kimi_claw")
        self.assertEqual(err.code, "connection")
        self.assertTrue(err.retryable)
        self.assertNotIn("claw-secret-2", str(err))

    def test_timeout_propagates_as_retryable_timeout(self):
        for exc in (socket.timeout("timed out"), TimeoutError("timed out")):
            def hang(request, body, exc=exc):
                raise exc

            opener = _RecordingOpener(hang)
            adapter = MoonshotAdapter(api_key="sk-test-secret-3", opener=opener)
            request = ChatRequest(messages=[Message(role=Role.USER, content="hi")], model="kimi-k2")
            with self.assertRaises(ProviderError) as caught:
                adapter.chat(request)
            self.assertEqual(caught.exception.code, "timeout")
            self.assertTrue(caught.exception.retryable)

    def test_invalid_timeout_config_fails_closed(self):
        with self.assertRaises(ProviderError) as caught:
            MoonshotAdapter(api_key="sk-x", timeout=-5)
        self.assertEqual(caught.exception.code, "config")

    def test_http_401_maps_to_authentication_error_without_secret_echo(self):
        secret = "sk-test-secret-4"

        def unauthorized(request, body):
            payload = ("invalid token " + secret).encode()
            raise urllib.error.HTTPError(request.full_url, 401, "Unauthorized", hdrs=None, fp=io.BytesIO(payload))

        opener = _RecordingOpener(unauthorized)
        adapter = MoonshotAdapter(api_key=secret, opener=opener)
        request = ChatRequest(messages=[Message(role=Role.USER, content="hi")], model="kimi-k2")
        with self.assertRaises(AuthenticationError) as caught:
            adapter.chat(request)
        self.assertNotIn(secret, str(caught.exception))

    def test_redirect_refused_fail_closed(self):
        def redirect(request, body):
            raise urllib.error.HTTPError(request.full_url, 302, "Found", hdrs={"Location": "https://evil.example/v1"}, fp=io.BytesIO(b""))

        opener = _RecordingOpener(redirect)
        adapter = MoonshotAdapter(api_key="sk-test-secret-5", opener=opener)
        request = ChatRequest(messages=[Message(role=Role.USER, content="hi")], model="kimi-k2")
        with self.assertRaises(ProviderError):
            adapter.chat(request)

    def test_concurrent_session_isolation(self):
        seen = {}

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(length).decode()
                auth = self.headers.get("Authorization", "")
                key = threading.current_thread().name
                seen.setdefault(key, []).append((auth, body))
                payload = json.dumps({"choices": [{"message": {"role": "assistant", "content": "ok"}}]}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f"http://127.0.0.1:{server.server_address[1]}/v1"
            adapters = [KimiClawAdapter(token=f"token-{i}", base_url=base) for i in range(4)]

            def call(adapter, i):
                request = ChatRequest(messages=[Message(role=Role.USER, content=f"m{i}")], model="kimi-claw")
                return adapter.chat(request)

            with contextlib.ExitStack() as stack:
                threads = [threading.Thread(target=call, args=(a, i)) for i, a in enumerate(adapters)]
                for t in threads:
                    t.start()
                for t in threads:
                    t.join()
            for records in seen.values():
                for auth, body in records:
                    self.assertTrue(auth.startswith("Bearer token-"))
                    self.assertNotIn("token-", body)
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
