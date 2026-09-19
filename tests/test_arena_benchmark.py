import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from contextlib import redirect_stdout
from unittest.mock import patch

from ai_providers import ChatRequest, ChatResponse, DEFAULT_REGISTRY, Message, ProviderName, Role
from ai_providers.adapters.arena_adapter import ArenaAdapter
from residual.eval.arena import (
    AgentEvaluationTrace,
    ArenaTraceEvent,
    extract_arena_aligned_signals,
)
from residual.modular import make_adapter, normalize_profile
from residual.cli import main as residual_main
from residual.eval_frozen.workload import development_workload
from residual.workbench.arena_benchmark import freeze_protocol, score_protocol
from residual.workbench.arena_live import run_protocol


def manifest(repeats=1):
    return {
        "schema_version": "residual.ax-arena-manifest.v1",
        "experiment_id": "AX-ARENA-TEST",
        "title": "test",
        "conditions": ["control", "residual"],
        "repeats": repeats,
        "seed": 7,
        "slice": "evaluation",
        "evidence_level": "development_fixture",
        "allow_provider_fallback": False,
        "workload": {"kind": "development_fixture"},
        "residual_signals": [],
    }


class ArenaIntegrationTests(unittest.TestCase):
    def test_top_level_arena_setup_prints_direct_keys_page(self):
        output = io.StringIO()
        with redirect_stdout(output):
            code = residual_main(["arena", "setup", "--print-only"])
        self.assertEqual(code, 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(
            payload["keys_url"],
            "https://portal.api.preview.arena.ai/dashboard/keys",
        )
        self.assertFalse(payload["opened_browser"])

    def test_provider_is_closed_registered_and_modular(self):
        self.assertEqual(ProviderName("arena").value, "arena")
        self.assertIn("arena", DEFAULT_REGISTRY.names())
        adapter = ArenaAdapter("secret", "http://127.0.0.1:1234")
        self.assertEqual(adapter.name, "arena")
        self.assertEqual(adapter._headers()["Authorization"], "Bearer secret")
        body = adapter._build_body(ChatRequest(
            "example-model",
            (Message(Role.USER, "hello"),),
        ))
        self.assertIs(body["allow_fallbacks"], False)
        self.assertNotIn("fallbacks", body)
        self.assertNotIn("fallback_on", body)
        profile = normalize_profile({
            "kind": "arena",
            "model": "example-model",
            "base_url": "https://api.preview.arena.ai/v1",
            "placement": "remote",
            "output_token_field": "max_completion_tokens",
        }, "remote")
        bridged = make_adapter(profile, {"api_key": "secret"})
        self.assertIsInstance(bridged, ArenaAdapter)
        self.assertFalse(bridged.supports_tools("opaque-model"))

    def test_trace_snapshots_input_and_extracts_arena_aligned_signals(self):
        mutable = {"name": "lookup"}
        events = [
            ArenaTraceEvent.build(0, "tool_call", mutable),
            ArenaTraceEvent.build(1, "tool_call", {"name": "invented"}),
            ArenaTraceEvent.build(2, "bash_result", {"ok": False}),
            ArenaTraceEvent.build(3, "bash_result", {"ok": False}),
            ArenaTraceEvent.build(4, "bash_result", {"ok": True}),
            ArenaTraceEvent.build(5, "correction", {"correction_id": "c1"}),
            ArenaTraceEvent.build(6, "correction_outcome", {"correction_id": "c1", "status": "accepted"}),
            ArenaTraceEvent.build(7, "feedback", {"sentiment": "praise"}),
            ArenaTraceEvent.build(8, "task_feedback", {"approved": True}),
        ]
        mutable["name"] = "changed-after-build"
        trace = AgentEvaluationTrace.build(
            experiment_id="AX-ARENA-TEST",
            observation_id="obs-1",
            task_id="task-1",
            condition="residual",
            model="arena:model-a",
            harness_version="test",
            environment_digest="env",
            available_tools=("lookup", "bash"),
            events=events,
            usage={"prompt_tokens": 10, "completion_tokens": 2, "cost_usd": 0.1},
            verdict={"state": "PASS", "verified_task_success": True},
            provider_metadata={"provider": "arena", "fallback_used": False},
        )
        self.assertEqual(trace.events[0].data["name"], "lookup")
        self.assertEqual(AgentEvaluationTrace.from_payload(trace.payload()).sha256, trace.sha256)
        signals = extract_arena_aligned_signals(trace)
        self.assertTrue(signals.confirmed_success)
        self.assertEqual(signals.tool_calls, 2)
        self.assertEqual(signals.tool_hallucinations, 1)
        self.assertEqual(signals.bash_failure_episodes, 1)
        self.assertEqual(signals.bash_recovered_episodes, 1)
        self.assertEqual(signals.bash_recovery_calls_total, 2)
        self.assertEqual(signals.steerability, 1.0)
        self.assertTrue(signals.praise_vs_complaint)

    def test_freeze_is_deterministic_and_score_is_paired(self):
        lock = freeze_protocol(manifest(), ["arena:model-a"])
        self.assertEqual(lock, freeze_protocol(manifest(), ["arena:model-a"]))
        self.assertEqual(len(lock["schedule"]), 12)

        traces = []
        for job in lock["schedule"]:
            success = job["condition"] == "residual"
            traces.append(AgentEvaluationTrace.build(
                experiment_id=job["experiment_id"],
                observation_id=job["observation_id"],
                task_id=job["task_id"],
                condition=job["condition"],
                model=job["model"],
                harness_version="test",
                environment_digest="env",
                available_tools=(),
                events=(),
                usage={"prompt_tokens": 1, "completion_tokens": 1, "cost_usd": 0.01},
                verdict={"state": "PASS" if success else "FAIL", "verified_task_success": success},
                provider_metadata={"provider": "arena", "fallback_used": False},
            ))
        report = score_protocol(lock, traces)
        self.assertEqual(report["summary"]["arena:model-a"]["control"]["scheduled_success_rate"], 0.0)
        self.assertEqual(report["summary"]["arena:model-a"]["residual"]["scheduled_success_rate"], 1.0)
        self.assertEqual(
            report["paired_success_comparisons"][0]["residual_minus_control_success_rate"],
            1.0,
        )

    def test_score_rejects_missing_observation(self):
        lock = freeze_protocol(manifest(), ["arena:model-a"])
        job = lock["schedule"][0]
        trace = AgentEvaluationTrace.build(
            experiment_id=job["experiment_id"],
            observation_id=job["observation_id"],
            task_id=job["task_id"],
            condition=job["condition"],
            model=job["model"],
            harness_version="test",
            environment_digest="env",
            available_tools=(),
            events=(),
            usage={"prompt_tokens": 1, "completion_tokens": 1},
            verdict={"state": "PASS", "verified_task_success": True},
            provider_metadata={},
        )
        with self.assertRaises(Exception):
            score_protocol(lock, [trace])

    def test_unknown_pair_remains_explicit(self):
        lock = freeze_protocol(manifest(), ["arena:model-a"])
        traces = []
        unknown_id = lock["schedule"][0]["observation_id"]
        for job in lock["schedule"]:
            unknown = job["observation_id"] == unknown_id
            traces.append(AgentEvaluationTrace.build(
                experiment_id=job["experiment_id"],
                observation_id=job["observation_id"],
                task_id=job["task_id"],
                condition=job["condition"],
                model=job["model"],
                harness_version="test",
                environment_digest="env",
                available_tools=(),
                events=(),
                usage={},
                verdict={
                    "state": "UNKNOWN" if unknown else "PASS",
                    "verified_task_success": None if unknown else True,
                },
                provider_metadata={"provider": "arena", "fallback_used": False},
            ))
        report = score_protocol(lock, traces)
        summary = report["summary"]["arena:model-a"]
        unknown_total = summary["control"]["unknown"] + summary["residual"]["unknown"]
        self.assertEqual(unknown_total, 1)
        paired = report["paired_success_comparisons"][0]
        self.assertEqual(paired["unknown_pairs"], 1)
        self.assertEqual(paired["complete_pairs"], 5)

    def test_live_runner_executes_control_and_real_residual_harness_without_network(self):
        live = manifest()
        live["evidence_level"] = "live_model"
        live["experiment_id"] = "AX-ARENA-LIVE-TEST"
        lock = freeze_protocol(live, ["arena:model-a"])
        answers = {
            task.prompt: task.expected
            for task in development_workload().slice_tasks("evaluation")
        }

        def fake_chat(_adapter, req):
            content = req.messages[-1].content
            try:
                packet = json.loads(content)
            except json.JSONDecodeError:
                packet = None
            if isinstance(packet, dict) and packet.get("protocol") == "residual.packet.v1":
                answer = answers[packet["goal"]]
                text = json.dumps(
                    {"updates": {"answer": answer}, "requests": []},
                    sort_keys=True,
                    separators=(",", ":"),
                )
            else:
                text = answers[content]
            return ChatResponse(
                req.model,
                text,
                usage={"prompt_tokens": 5, "completion_tokens": 1, "total_tokens": 6},
            )

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "arena-run"
            with patch.dict(os.environ, {"ARENA_API_KEY": "test-key"}), patch.object(
                ArenaAdapter, "chat", new=fake_chat
            ):
                traces = run_protocol(
                    lock, output, max_output_tokens=64, residual_rounds=1
                )
            self.assertEqual(len(traces), 12)
            self.assertTrue((output / "protocol.json").is_file())
            self.assertTrue((output / "environment.json").is_file())
            self.assertEqual(
                len((output / "traces.jsonl").read_text().splitlines()), 12
            )
            report = score_protocol(lock, traces)
            self.assertEqual(
                report["summary"]["arena:model-a"]["control"]["scheduled_success_rate"],
                1.0,
            )
            self.assertEqual(
                report["summary"]["arena:model-a"]["residual"]["scheduled_success_rate"],
                1.0,
            )


if __name__ == "__main__":
    unittest.main()
