from __future__ import annotations
import json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from residual.core import ContractError
from residual.station.service import Station
from residual.station.models import save_settings
from residual import research_runtime as rr

class ResearchRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.s=Station(self.tmp.name)
    def tearDown(self): self.tmp.cleanup()
    def test_safe_experiment_ids(self):
        self.assertEqual(rr._safe_id("M6-WB-001"),"M6-WB-001")
        for bad in ("../x","x","M6/spec",""):
            with self.assertRaises(ContractError): rr._safe_id(bad)
    def test_list_runs_ignores_garbage(self):
        root=rr.workbench_root(self.s); (root/"junk").mkdir()
        self.assertEqual(rr.list_runs(self.s),[])
    def test_prepare_rejects_definition_drift_after_retained_run(self):
        exp={"id":"M6-WB-001","adapter":"workbench_json_pilot"}
        old={"id":"M6-WB-001","adapter":"different"}
        root=rr.workbench_root(self.s)/"M6-WB-001"/"20260919T000000Z-1234abcd"; root.mkdir(parents=True)
        (root/"manifest.json").write_text(json.dumps({"experiment_id":"M6-WB-001","experiment_sha256":rr.research._sha(rr.research._json_bytes(old))}))
        with patch("residual.research_runtime.research.sync", return_value=({"schema_version":1,"experiments":[exp]},"a"*40)):
            with self.assertRaises(ContractError): rr.prepare(self.s,"M6-WB-001")


    def test_prepare_enforces_preregistered_trial_limit(self):
        exp={"id":"M6-WB-001","adapter":"m6_improvementspec","status":"runnable","trials":1}
        root=rr.workbench_root(self.s)/"M6-WB-001"/"20260919T000000Z-1234abcd"; root.mkdir(parents=True)
        sha=rr.research._sha(rr.research._json_bytes(exp))
        (root/"manifest.json").write_text(json.dumps({"experiment_id":"M6-WB-001","experiment_sha256":sha,"run_status":"COMPLETED"}))
        with patch("residual.research_runtime.research.sync", return_value=({"schema_version":1,"experiments":[exp]},"a"*40)):
            with self.assertRaisesRegex(ContractError,"authoritative trials"):
                rr.prepare(self.s,"M6-WB-001")

    def test_workbench_adapter_executes_full_governed_path_without_candidate_code(self):
        save_settings(self.s.store, {
            "local": {
                "kind": "ollama",
                "model": "qwen2.5-coder:test",
                "base_url": "http://127.0.0.1:11434",
                "output_token_field": "max_tokens",
            }
        })
        exp = {
            "id": "M6-WB-001",
            "adapter": "workbench_json_pilot",
            "status": "runnable",
            "hypothesis": "smoke",
            "acceptance_policy": "frozen",
            "frozen_controls": {
                "max_output_tokens": 1600,
                "batch_max_passes": 5,
                "batch_token_budget": 30000,
                "batch_wall_clock_s": 600,
            },
        }
        out = rr.workbench_root(self.s) / "smoke"
        out.mkdir(parents=True)
        payload = json.dumps(rr.PILOT_DOCUMENT, separators=(",", ":"))
        with patch.object(
            self.s.ollama,
            "status",
            return_value={
                "connected": True,
                "cpu_count": 4,
                "models": [{"name": "qwen2.5-coder:test", "size": 1}],
            },
        ), patch("residual.station.service.model_call") as call:
            def reply(store, pid, role, packet, system, schema, placement, tid, *, extensions=None):
                if role == "runner":
                    return {"files": {"research/workbench_result.json": payload}}
                return {"approved": True, "findings": []}
            call.side_effect = reply
            evidence = rr._workbench_json_pilot(self.s, out, exp, lambda *args: None)

        self.assertEqual(evidence["outcome"], "PASS")
        self.assertEqual(evidence["task"]["state"], "integrated")
        self.assertTrue(evidence["task"]["verification_receipt"])
        self.assertEqual(json.loads(evidence["generated_artifact"]), rr.PILOT_DOCUMENT)
        self.assertTrue((out / "events.jsonl").read_text().strip())
        self.assertFalse(any(check["kind"] == "command" for check in evidence["task"]["checks_result"]))

    def test_staged_adapter_fails_closed(self):
        out=rr.workbench_root(self.s)/"M6-SCALE-001"/"20260919T000000Z-1234abcd"; out.mkdir(parents=True)
        (out/"manifest.json").write_text(json.dumps({"experiment_id":"M6-SCALE-001","run_id":out.name,"run_status":"PREPARED"}))
        (out/"experiment.json").write_text(json.dumps({"id":"M6-SCALE-001","adapter":None}))
        with self.assertRaises(ContractError): rr.run(self.s,"M6-SCALE-001",out.name)
