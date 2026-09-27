from __future__ import annotations

from dataclasses import dataclass
import unittest

from residual.core import ContractError
from residual.station.mesh_runner import MeshClawRunner, provider_plan


@dataclass
class Result:
    text: str
    provider: str
    model: str
    transport: str
    provider_attempts: tuple
    usage: dict
    raw_digest: str = "0" * 64


class FakeClient:
    def __init__(self, work):
        self.work = work
        self.snapshots = {}
        self.admitted = None
        self.submitted = None
    def recover_outbox(self): return {}
    def sync(self, pid):
        snap = {"generation": self.work["generation"]}
        self.snapshots[pid] = snap
        return snap
    def claim(self, pid):
        work, self.work = self.work, None
        return work
    def execution_admit(self, work, attempts):
        self.admitted = attempts
        return {"admitted": True}
    def submit_result(self, work, **kwargs):
        self.submitted = kwargs
        return {"state": "review_ready"}


class FakeAdapter:
    def __init__(self, result):
        self.result = result
        self.cancelled = []
    def execute(self, assignment): return self.result
    def cancel(self, assignment): self.cancelled.append(assignment); return {"observed_stopped": True}
    def shutdown(self): return []


def work(policy=None):
    return {
        "project_id": "p-1", "generation": 1, "task_id": "T-1", "attempt": 1,
        "lease_id": "lease", "fencing_token": 1, "route": "local",
        "packet": {"instruction": "x", "execution_policy": policy or {
            "placements": ["local"], "models": [], "max_provider_attempts": 1,
            "cross_placement": False}},
    }


class MeshRunnerTests(unittest.TestCase):
    def test_provider_plan_prefers_task_route(self):
        w = work({"placements": ["local", "remote"],
                  "models": ["remote/a", "local/b"], "max_provider_attempts": 2,
                  "cross_placement": True})
        plan = provider_plan(w, [
            {"placement": "remote", "model": "remote/a"},
            {"placement": "local", "model": "local/b"},
        ], 100)
        self.assertEqual([x["model"] for x in plan], ["local/b", "remote/a"])

    def test_cross_placement_not_invented(self):
        w = work()
        with self.assertRaises(ContractError):
            provider_plan(w, [{"placement": "remote", "model": "remote/a"}], 100)

    def test_execution_is_pre_admitted_and_result_is_submitted(self):
        w = work()
        client = FakeClient(w)
        adapter = FakeAdapter(Result(
            '{"files":{"a.py":"x=1"}}', "ollama", "local/a", "embedded_exec",
            ({"placement":"local","model":"local/a","request_bytes":64050,
              "status":"completed","reason":"success","usage_known":True},),
            {"input": 10, "output": 4},
        ))
        runner = MeshClawRunner(
            client, adapter, project_id="p-1",
            provider_routes=[{"placement": "local", "model": "local/a"}])
        result = runner.run_once()
        self.assertEqual(result["state"], "review_ready")
        self.assertEqual(client.admitted[0]["model"], "local/a")
        self.assertEqual(client.submitted["response"]["files"]["a.py"], "x=1")

    def test_failure_is_not_blindly_replayed(self):
        class Failing(FakeAdapter):
            def execute(self, assignment):
                raise RuntimeError("transport uncertain")
        client = FakeClient(work())
        adapter = Failing(None)
        runner = MeshClawRunner(client, adapter, project_id="p-1",
            provider_routes=[{"placement": "local", "model": "local/a"}])
        with self.assertRaises(RuntimeError):
            runner.run_once()
        self.assertIsNone(client.submitted)

    def test_unadmitted_winner_is_rejected(self):
        client = FakeClient(work())
        adapter = FakeAdapter(Result(
            '{"files":{"a.py":"x=1"}}', "other", "unapproved/model", "embedded_exec",
            (), {"input": 1, "output": 1},
        ))
        runner = MeshClawRunner(client, adapter, project_id="p-1",
            provider_routes=[{"placement": "local", "model": "local/a"}])
        with self.assertRaises(ContractError):
            runner.run_once()
        self.assertIsNone(client.submitted)

    def test_oversized_request_is_rejected_before_execution_admission(self):
        w = work()
        w["packet"]["instruction"] = "x" * 100
        client = FakeClient(w)
        adapter = FakeAdapter(None)
        runner = MeshClawRunner(client, adapter, project_id="p-1",
            provider_routes=[{"placement": "local", "model": "local/a"}], max_request_bytes=64_050)
        with self.assertRaises(ContractError):
            runner.run_once()
        self.assertIsNone(client.admitted)


if __name__ == "__main__":
    unittest.main()
