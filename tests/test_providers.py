import contextlib
import json
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from residual.core import ContractError, canonical
from residual.providers import HTTPProvider, Prices, ProviderError, Usage


@contextlib.contextmanager
def server(response, status=200, headers=None):
    requests = []
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            body = self.rfile.read(int(self.headers["Content-Length"]))
            requests.append({"path": self.path, "body": body, "headers": dict(self.headers)})
            self.send_response(status)
            for key, value in (headers or {}).items():
                self.send_header(key, value)
            self.end_headers()
            data = response if isinstance(response, bytes) else json.dumps(response).encode()
            self.wfile.write(data)
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_port}", requests
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)


class ProviderTests(unittest.TestCase):
    packet = {"goal": "Unicode evidence: café, 日本語", "obligations": []}

    def test_native_ollama_real_http_contract_and_byte_accounting(self):
        envelope = {"message": {"content": '{"updates":{},"requests":[]}'}, "done": True,
                    "done_reason": "stop", "prompt_eval_count": 52, "eval_count": 12,
                    "prompt_eval_cached_count": 10}
        with server(envelope) as (url, requests):
            p = HTTPProvider("ollama", "installed-model", url, "local")
            result = p.generate(self.packet, 333)
        self.assertEqual(requests[0]["path"], "/api/chat")
        data = json.loads(requests[0]["body"])
        self.assertFalse(data["stream"])
        self.assertEqual(data["options"]["num_predict"], 333)
        self.assertEqual(data["format"]["type"], "object")
        self.assertEqual(p.wire_size(self.packet, 333), len(requests[0]["body"]))
        self.assertEqual(result.usage, Usage(52, 12, 10, "reported"))

    def test_openai_compatible_real_http_contract(self):
        envelope = {"choices": [{"message": {"content": '{"updates":{},"requests":[]}'}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 31, "completion_tokens": 11,
                              "prompt_tokens_details": {"cached_tokens": 5}}}
        with server(envelope) as (url, requests):
            p = HTTPProvider("openai_compatible", "any-model", url + "/v1", "remote")
            result = p.generate(self.packet, 222)
        data = json.loads(requests[0]["body"])
        self.assertEqual(requests[0]["path"], "/v1/chat/completions")
        self.assertEqual(data["max_completion_tokens"], 222)
        self.assertEqual(data["response_format"], {"type": "json_object"})
        self.assertEqual(result.usage, Usage(31, 11, 5, "reported"))
        self.assertEqual(p.wire_size(self.packet, 222), len(requests[0]["body"]))

    def test_legacy_max_tokens_and_json_mode_off(self):
        p = HTTPProvider("openai_compatible", "model", "https://example.com/v1", "remote",
                         json_mode=False, output_token_field="max_tokens")
        data = p.payload(self.packet, 321)
        self.assertEqual(data["max_tokens"], 321)
        self.assertNotIn("response_format", data)

    def test_api_key_only_in_authorization_header(self):
        os.environ["RESIDUAL_TEST_API_KEY"] = "test-secret"
        try:
            with server({"choices": [{"message": {"content": "{}"}}]}) as (url, requests):
                p = HTTPProvider("openai_compatible", "model", url + "/v1", "remote", api_key_env="RESIDUAL_TEST_API_KEY")
                p.generate(self.packet, 50)
            self.assertEqual(requests[0]["headers"]["Authorization"], "Bearer test-secret")
            self.assertNotIn(b"test-secret", requests[0]["body"])
        finally:
            os.environ.pop("RESIDUAL_TEST_API_KEY", None)

    def test_http_errors_do_not_echo_server_body_or_key(self):
        with server(b'private-server-message: SECRET', status=401) as (url, requests):
            p = HTTPProvider("openai_compatible", "model", url, "remote")
            with self.assertRaisesRegex(ProviderError, "^http_401$"):
                p.generate(self.packet, 10)

    def test_redirects_are_never_followed(self):
        with server(b"", status=307, headers={"Location": "https://example.com/leak"}) as (url, requests):
            p = HTTPProvider("ollama", "model", url, "local")
            with self.assertRaisesRegex(ProviderError, "http_redirect_refused"):
                p.generate(self.packet, 10)
        self.assertEqual(len(requests), 1)

    def test_incomplete_ollama_response_rejected(self):
        with server({"message": {"content": "{}"}, "done": False}) as (url, requests):
            p = HTTPProvider("ollama", "model", url, "local")
            with self.assertRaisesRegex(ProviderError, "ollama_incomplete_response"):
                p.generate(self.packet, 10)

    def test_absent_usage_remains_unknown(self):
        with server({"choices": [{"message": {"content": "{}"}}]}) as (url, requests):
            result = HTTPProvider("openai_compatible", "model", url, "remote").generate(self.packet, 10)
        self.assertEqual(result.usage.source, "unavailable")
        self.assertIsNone(result.usage.input_tokens)

    def test_invalid_usage_rejected(self):
        with server({"message": {"content": "{}"}, "done": True,
                     "prompt_eval_count": -1, "eval_count": 10}) as (url, requests):
            with self.assertRaisesRegex(ProviderError, "invalid_provider_response_envelope"):
                HTTPProvider("ollama", "model", url, "local").generate(self.packet, 10)

    def test_malformed_json_and_oversized_response_rejected(self):
        for body in (b"not-json", b"x" * 2_000_001):
            with server(body) as (url, requests):
                with self.assertRaises(ProviderError):
                    HTTPProvider("ollama", "model", url, "local").generate(self.packet, 10)

    def test_missing_key_errors_before_transport(self):
        with server({}) as (url, requests):
            p = HTTPProvider("openai_compatible", "model", url, "remote", api_key_env="RESIDUAL_NONEXISTENT_TEST_KEY")
            with self.assertRaisesRegex(ProviderError, "missing_api_key_environment_variable"):
                p.generate(self.packet, 10)
            self.assertEqual(requests, [])

    def test_remote_endpoints_cannot_be_labelled_local(self):
        for url in ("https://api.example.com", "http://192.168.1.5:11434"):
            with self.assertRaises(ContractError):
                HTTPProvider("ollama", "model", url, "local")

    def test_insecure_remote_endpoints_and_embedded_credentials_rejected(self):
        for url in ("http://api.example.com", "https://user:secret@example.com", "https://example.com/?key=secret"):
            with self.assertRaises(ContractError):
                HTTPProvider("openai_compatible", "model", url, "remote")

    def test_options_cannot_override_budget_or_messages(self):
        for options in ({"max_tokens": 999999}, {"num_predict": -1}, {"messages": []}):
            with self.assertRaises(ContractError):
                HTTPProvider("ollama", "model", "http://localhost:11434", "local", options=options)

    def test_prices_use_reported_tokens_and_separate_cached_tokens(self):
        prices = Prices(10, 20, 2)
        self.assertAlmostEqual(prices.cost(Usage(100, 20, 50, "reported")), 0.001)
        self.assertIsNone(prices.cost(Usage(100, 20, 50, "simulation")))
        self.assertIsNone(prices.cost(Usage(100, 20, None, "reported")))
        self.assertIsNone(prices.cost(Usage()))

    def test_invalid_prices_rejected(self):
        for value in (-1, float("nan"), float("inf"), True):
            with self.assertRaises(ContractError):
                Prices(value, 1)


if __name__ == "__main__":
    unittest.main()
