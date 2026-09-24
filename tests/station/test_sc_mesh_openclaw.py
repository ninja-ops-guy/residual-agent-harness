from __future__ import annotations

import json
import unittest

from residual.core import ContractError
from residual.station.claw_adapter import (
    _fallback_attempts, _final_text, _tool_calls, _winner, parse_openclaw_json,
)


class OpenClawAdapterContractTests(unittest.TestCase):
    def test_stable_exec_envelope_parses(self):
        raw = json.dumps({
            "ok": True, "status": "ok", "final": '{"files":{"a.py":"x=1"}}',
            "provider": "ollama", "model": "qwen2.5-coder:7b",
            "usage": {"input": 10, "output": 4, "total": 14},
            "toolSummary": {"calls": 0, "tools": []},
        })
        value = parse_openclaw_json("diagnostic\n" + raw)
        self.assertEqual(_final_text(value), '{"files":{"a.py":"x=1"}}')
        self.assertEqual(_winner(value), ("ollama", "qwen2.5-coder:7b"))
        self.assertEqual(_tool_calls(value), 0)

    def test_tool_use_is_visible(self):
        value = {"toolSummary": {"calls": 2}}
        self.assertEqual(_tool_calls(value), 2)

    def test_missing_tool_use_evidence_fails_closed(self):
        with self.assertRaises(ContractError):
            _tool_calls({})
        with self.assertRaises(ContractError):
            _tool_calls({"toolSummary": {}})

    def test_malformed_or_ambiguous_stdout_rejected(self):
        with self.assertRaises(ContractError):
            parse_openclaw_json("not json")
        with self.assertRaises(ContractError):
            parse_openclaw_json('{"ok":true}\ntrailing')

    def test_fallback_attempts_must_match_admitted_plan(self):
        plan = [
            {"placement": "remote", "model": "kimi/kimi-code", "request_bytes": 100},
            {"placement": "local", "model": "ollama/qwen2.5-coder:7b", "request_bytes": 100},
        ]
        value = {"meta": {"agentMeta": {"fallbackAttempts": [
            {"provider": "kimi", "model": "kimi-code", "reason": "rate_limit"}
        ]}}}
        attempts = _fallback_attempts(value, plan)
        self.assertEqual(attempts[0]["status"], "failed")
        bad = {"fallbackAttempts": [{"provider": "other", "model": "model", "reason": "x"}]}
        with self.assertRaises(ContractError):
            _fallback_attempts(bad, plan)


if __name__ == "__main__":
    unittest.main()
