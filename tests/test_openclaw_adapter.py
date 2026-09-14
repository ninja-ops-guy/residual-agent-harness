import json
import unittest

from residual.core import ContractError
from residual.engines import CapabilityRouter, ContextAssembly, TaskSpec
from residual.engines.openclaw_adapter import OpenClawConfig, OpenClawEngine


class RecordingTransport:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def __call__(self, endpoint, body, headers, timeout_s):
        self.calls.append((endpoint, body, headers, timeout_s))
        return self.response


class OpenClawAdapterTests(unittest.TestCase):
    def config(self, **kwargs):
        values = {
            "model": "provider/model",
            "gateway_url": "http://127.0.0.1:18789",
            "token": "secret-token",
            "openclaw_version": "test",
            "capabilities": ("agent", "code"),
        }
        values.update(kwargs)
        return OpenClawConfig(**values)

    def test_router_registration_requires_no_special_case(self):
        engine = OpenClawEngine(self.config(), transport=RecordingTransport({"output_text": "ok"}))
        router = CapabilityRouter()
        router.register(engine, ("agent", "code"))
        self.assertIs(router.select("agent"), engine)

    def test_request_is_deterministic_and_context_is_separate(self):
        transport = RecordingTransport({"output_text": "ok"})
        engine = OpenClawEngine(self.config(), transport=transport)
        task = TaskSpec("t1", "agent", {"b": 2, "a": 1}, {"instructions": "do work"})
        context = ContextAssembly({"z": 3, "y": 2})
        engine.execute(task, context)
        engine.execute(task, context)
        first = transport.calls[0][1]
        second = transport.calls[1][1]
        self.assertEqual(first, second)
        decoded = json.loads(first["input"])
        self.assertEqual(decoded["task_id"], "t1")
        self.assertEqual(decoded["task"], {"a": 1, "b": 2})
        self.assertEqual(decoded["context"], {"y": 2, "z": 3})
        self.assertEqual(first["instructions"], "do work")

    def test_gateway_endpoint_timeout_and_auth(self):
        transport = RecordingTransport({"output_text": "ok"})
        engine = OpenClawEngine(self.config(timeout_s=17.5), transport=transport)
        result = engine.execute(TaskSpec("t", "agent", "x"), ContextAssembly())
        endpoint, _, headers, timeout_s = transport.calls[0]
        self.assertEqual(endpoint, "http://127.0.0.1:18789/v1/responses")
        self.assertEqual(timeout_s, 17.5)
        self.assertEqual(headers["Authorization"], "Bearer secret-token")
        self.assertNotIn("secret-token", repr(result.raw_metadata))

    def test_output_text_and_total_tokens_normalize(self):
        engine = OpenClawEngine(self.config(), transport=RecordingTransport({}))
        result = engine.normalize({"id": "r1", "output_text": "hello", "usage": {"total_tokens": 11}})
        self.assertEqual(result.candidate, "hello")
        self.assertEqual(result.token_usage, 11)
        self.assertEqual(result.raw_metadata["response_id"], "r1")

    def test_responses_message_and_split_usage_normalize(self):
        engine = OpenClawEngine(self.config(), transport=RecordingTransport({}))
        result = engine.normalize({
            "output": [{"id": "m1", "type": "message", "content": [
                {"type": "output_text", "text": "hello "},
                {"type": "output_text", "text": "world"},
            ]}],
            "usage": {"input_tokens": 4, "output_tokens": 6},
        })
        self.assertEqual(result.candidate, "hello world")
        self.assertEqual(result.token_usage, 10)
        self.assertEqual(result.engine_trace, ({"id": "m1", "type": "message"},))

    def test_chat_choices_normalize(self):
        engine = OpenClawEngine(self.config(), transport=RecordingTransport({}))
        result = engine.normalize({
            "choices": [{"message": {"content": "chat reply"}}],
            "usage": {"prompt_tokens": 3, "completion_tokens": 5},
        })
        self.assertEqual(result.candidate, "chat reply")
        self.assertEqual(result.token_usage, 8)

    def test_allowed_tool_succeeds(self):
        transport = RecordingTransport({
            "output_text": "done",
            "output": [{"type": "function_call", "name": "read", "call_id": "c1"}],
        })
        engine = OpenClawEngine(self.config(), transport=transport)
        task = TaskSpec("t", "agent", "x", {"allowed_tools": ("read",)})
        result = engine.execute(task, ContextAssembly())
        self.assertEqual(result.tool_calls[0]["name"], "read")

    def test_forbidden_tool_fails_closed(self):
        transport = RecordingTransport({
            "output": [{"type": "function_call", "name": "exec", "call_id": "c1"}],
        })
        engine = OpenClawEngine(self.config(), transport=transport)
        task = TaskSpec("t", "agent", "x", {"worker_contract": {"allowed_tools": ["read"]}})
        with self.assertRaisesRegex(ContractError, "forbidden tool"):
            engine.execute(task, ContextAssembly())

    def test_runtime_identity_is_observed_not_inferred(self):
        with_runtime = OpenClawEngine(self.config(), transport=RecordingTransport({}))
        result = with_runtime.normalize({"output_text": "ok", "metadata": {"agentHarnessId": "codex"}})
        self.assertEqual(result.raw_metadata["openclaw_runtime"], "codex")
        self.assertTrue(result.raw_metadata["runtime_identity_verified"])

        without_runtime = with_runtime.normalize({"output_text": "ok"})
        self.assertIsNone(without_runtime.raw_metadata["openclaw_runtime"])
        self.assertIsNone(without_runtime.raw_metadata["runtime_identity_verified"])

    def test_requested_runtime_mismatch_is_recorded(self):
        transport = RecordingTransport({"output_text": "ok", "agentHarnessId": "openclaw"})
        engine = OpenClawEngine(self.config(), transport=transport)
        task = TaskSpec("t", "agent", "x", {"openclaw_runtime_id": "codex"})
        result = engine.execute(task, ContextAssembly())
        self.assertEqual(result.raw_metadata["openclaw_runtime"], "openclaw")
        self.assertFalse(result.raw_metadata["runtime_identity_verified"])

    def test_health_has_no_transport_side_effect(self):
        transport = RecordingTransport({"output_text": "should not run"})
        engine = OpenClawEngine(self.config(), transport=transport)
        self.assertEqual(engine.health().value, "healthy")
        self.assertEqual(transport.calls, [])

    def test_invalid_configuration_fails_early(self):
        with self.assertRaises(ContractError):
            OpenClawConfig(model="", gateway_url="http://127.0.0.1:18789")
        with self.assertRaises(ContractError):
            OpenClawConfig(model="x", gateway_url="not-a-url")


if __name__ == "__main__":
    unittest.main()
