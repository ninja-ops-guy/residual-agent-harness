from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from residual.integrations.openclaw_bridge import (
    BridgeConfig,
    BridgeState,
    OpenClawResult,
    OpenClawSharedCommsBridge,
    addressed_prompt,
    deterministic_response_operation_id,
    deterministic_session_key,
    extract_openclaw_json,
    _openclaw_child_env,
    _sanitize_fallback_attempts,
)


class FakeClient:
    def __init__(self, messages):
        self._messages = list(messages)
        self.sent = []
        self.receipts = {}

    def recover_outbox(self, state):
        return 0

    def messages(self, project, after, thread):
        return [m for m in self._messages if int(m["seq"]) > after and m.get("thread_id") == thread]

    def send_durable(self, payload, state):
        state.enqueue(payload)
        self.sent.append(dict(payload))
        receipt = {"seq": 900 + len(self.sent)}
        self.receipts[payload["operation_id"]] = receipt
        state.ack(payload["operation_id"], receipt)
        return receipt


class FakeRunner:
    def __init__(self):
        self.calls = []

    def stop(self):
        pass

    def run(self, prompt, session_key):
        self.calls.append((prompt, session_key))
        return OpenClawResult(
            text="BRIDGE_OK",
            provider="ollama",
            model="qwen2.5-coder:7b",
            transport="embedded",
            fallback_from="gateway",
            fallback_attempts=[{"provider": "kimi", "reason": "rate_limit", "status": 429}],
        )


class FakeWarmer:
    def ensure_ready(self):
        return "already-loaded"


class OpenClawBridgeTests(unittest.TestCase):
    def test_addressing_is_strict_and_ignores_self(self):
        self.assertEqual(
            addressed_prompt({"actor": "operator", "message": "@OPENCLAW-A hello"}, "@OPENCLAW-A", "OPENCLAW-A"),
            "hello",
        )
        self.assertIsNone(addressed_prompt({"actor": "operator", "message": "@OPENCLAW-AB hello"}, "@OPENCLAW-A", "OPENCLAW-A"))
        self.assertIsNone(addressed_prompt({"actor": "remote:OPENCLAW-A", "message": "@OPENCLAW-A loop"}, "@OPENCLAW-A", "OPENCLAW-A"))

    def test_ids_are_deterministic_and_request_bound(self):
        one = deterministic_response_operation_id("p", "main", 12, "OPENCLAW-A")
        two = deterministic_response_operation_id("p", "main", 12, "OPENCLAW-A")
        other = deterministic_response_operation_id("p", "main", 13, "OPENCLAW-A")
        self.assertEqual(one, two)
        self.assertNotEqual(one, other)
        self.assertEqual(
            deterministic_session_key("p", "main", 12, "agent"),
            deterministic_session_key("p", "main", 12, "agent"),
        )

    def test_extracts_openclaw_json_after_noise(self):
        raw = 'warning\n' + json.dumps({"payloads": [{"text": "OK"}], "meta": {"agentMeta": {"provider": "ollama"}}}) + '\n'
        parsed = extract_openclaw_json(raw)
        self.assertEqual(parsed["payloads"][0]["text"], "OK")

    def test_child_env_scrubs_residual_credentials(self):
        import os
        saved = {key: os.environ.get(key) for key in ("RESIDUAL_WORKER_TOKEN", "RESIDUAL_RUNNER_API_KEY")}
        try:
            os.environ["RESIDUAL_WORKER_TOKEN"] = "secret"
            os.environ["RESIDUAL_RUNNER_API_KEY"] = "runner-secret"
            env = _openclaw_child_env()
            self.assertNotIn("RESIDUAL_WORKER_TOKEN", env)
            self.assertNotIn("RESIDUAL_RUNNER_API_KEY", env)
        finally:
            for key, value in saved.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_fallback_evidence_drops_raw_error_text(self):
        sanitized = _sanitize_fallback_attempts([{
            "provider": "kimi", "model": "kimicode", "reason": "rate_limit",
            "status": 429, "error": "secret-bearing raw blob"
        }])
        self.assertEqual(sanitized, [{
            "provider": "kimi", "model": "kimicode", "reason": "rate_limit", "status": 429
        }])
        self.assertNotIn("error", sanitized[0])

    def test_prepared_response_survives_reopen(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "state.sqlite3"
            state = BridgeState(path)
            row = state.ensure_inbox("p", "main", 7, "op", "hello")
            self.assertEqual(row["status"], "pending")
            state.prepare_response("p", "main", 7, {"payload": {"operation_id": "op", "message": "OK"}})
            state.close()
            reopened = BridgeState(path)
            row = reopened.inbox("p", "main", 7)
            self.assertEqual(row["status"], "prepared")
            self.assertEqual(json.loads(row["response_json"])["payload"]["message"], "OK")
            reopened.close()

    def test_outbox_rejects_operation_conflict(self):
        with tempfile.TemporaryDirectory() as td:
            state = BridgeState(Path(td) / "state.sqlite3")
            payload = {"operation_id": "op-1", "message": "hello"}
            state.enqueue(payload)
            state.enqueue(payload)
            with self.assertRaises(Exception):
                state.enqueue({"operation_id": "op-1", "message": "changed"})
            self.assertEqual(len(state.pending_outbox()), 1)
            state.close()

    def test_one_addressed_message_invokes_agent_and_receipts_response(self):
        with tempfile.TemporaryDirectory() as td:
            state = BridgeState(Path(td) / "state.sqlite3")
            status = Path(td) / "status.json"
            config = BridgeConfig(
                station="http://127.0.0.1:8765",
                project="p-1",
                profile="agent2",
                agent="roofbot-reviewer",
                name="OPENCLAW-AGENT2",
                address="@OPENCLAW-AGENT2",
                thread="openclaw-pilot",
                poll_seconds=1,
                timeout_s=30,
                max_attempts=3,
                max_batch=1,
                start_at="zero",
                advisory_prefix="ADVISORY\n\n",
                status_file=status,
            )
            client = FakeClient([
                {"seq": 1, "actor": "operator", "thread_id": "openclaw-pilot", "message": "noise"},
                {"seq": 2, "actor": "remote:R34-OPERATOR", "thread_id": "openclaw-pilot", "message": "@OPENCLAW-AGENT2 say ok"},
            ])
            runner = FakeRunner()
            bridge = OpenClawSharedCommsBridge(config, state, client, runner, FakeWarmer())
            handled = bridge.run_once()
            self.assertEqual(handled, 1)
            self.assertEqual(len(runner.calls), 1)
            self.assertEqual(len(client.sent), 1)
            self.assertEqual(client.sent[0]["message"], "BRIDGE_OK")
            self.assertEqual(state.cursor("p-1", "openclaw-pilot", "OPENCLAW-AGENT2"), 2)
            row = state.inbox("p-1", "openclaw-pilot", 2)
            self.assertEqual(row["status"], "done")
            report = json.loads(status.read_text())
            self.assertEqual(report["provider"], "ollama")
            self.assertEqual(report["model"], "qwen2.5-coder:7b")
            self.assertEqual(report["last_request_seq"], 2)
            state.close()

    def test_fresh_bridge_defaults_to_latest_without_replaying_history(self):
        with tempfile.TemporaryDirectory() as td:
            state = BridgeState(Path(td) / "state.sqlite3")
            status = Path(td) / "status.json"
            config = BridgeConfig(
                station="http://127.0.0.1:8765", project="p", profile="agent2", agent="roofbot-reviewer",
                name="OPENCLAW-AGENT2", address="@OPENCLAW-AGENT2", thread="main", poll_seconds=1,
                timeout_s=30, max_attempts=3, max_batch=1, start_at="latest", advisory_prefix="", status_file=status,
            )
            client = FakeClient([
                {"seq": 323, "actor": "operator", "thread_id": "main", "message": "@OPENCLAW-AGENT2 old request"},
                {"seq": 324, "actor": "remote:OPENCLAW-AGENT2", "thread_id": "main", "message": "old response"},
            ])
            runner = FakeRunner()
            bridge = OpenClawSharedCommsBridge(config, state, client, runner)
            self.assertEqual(bridge.run_once(), 0)
            self.assertEqual(state.cursor("p", "main", "OPENCLAW-AGENT2"), 324)
            self.assertEqual(runner.calls, [])
            report = json.loads(status.read_text())
            self.assertEqual(report["initialized_at_seq"], 324)
            state.close()

    def test_replay_after_done_does_not_reinvoke_agent(self):
        with tempfile.TemporaryDirectory() as td:
            state = BridgeState(Path(td) / "state.sqlite3")
            status = Path(td) / "status.json"
            config = BridgeConfig(
                station="http://127.0.0.1:8765", project="p", profile="agent2", agent="roofbot-reviewer",
                name="OPENCLAW-AGENT2", address="@OPENCLAW-AGENT2", thread="main", poll_seconds=1,
                timeout_s=30, max_attempts=3, max_batch=1, start_at="zero", advisory_prefix="", status_file=status,
            )
            message = {"seq": 5, "actor": "operator", "thread_id": "main", "message": "@OPENCLAW-AGENT2 hello"}
            client = FakeClient([message])
            runner = FakeRunner()
            bridge = OpenClawSharedCommsBridge(config, state, client, runner)
            self.assertEqual(bridge.run_once(), 1)
            state.set_cursor("p", "main", "OPENCLAW-AGENT2", 0)
            self.assertEqual(bridge.run_once(), 0)
            self.assertEqual(len(runner.calls), 1)
            self.assertEqual(len(client.sent), 1)
            state.close()


if __name__ == "__main__":
    unittest.main()
