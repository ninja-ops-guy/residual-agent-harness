import unittest
from residual.research.execution import ArmExecution, execute_trial, metrics_from_external_measurement, metrics_from_residual_result
from residual.research.nested_swarm import METRICS, build_manifest

class NestedSwarmExecutionTests(unittest.TestCase):
    def manifest(self):
        return build_manifest(registered_at="2026-09-19T14:00:00Z",task_corpus_sha256="a"*64,runtime_revision="head",trials_per_arm=1)
    def residual_result(self):
        return {"success":True,"trace_root":"d"*64,"metrics":{"total_obligations":2,"accepted_obligations":2,"elapsed_ms":20.0,"remote_cost_usd":0.02,"repeated_dispatch_calls":0,"evidence_requests":1,"failed_tool_calls":0,"human_interventions":0,"integration_conflicts":0},"calls":[{"usage":{"input_tokens":10,"output_tokens":4}}]}
    def external_metrics(self):
        return {"task_success":True,"verifier_pass_rate":1.0,"elapsed_ms":30.0,"input_tokens":12,"output_tokens":5,"api_cost_usd":0.03,"provider_calls":1,"retries":0,"evidence_requests":0,"failed_tool_calls":0,"human_interventions":0,"integration_conflicts":0,"duplicate_work_items":0,"convergence_iterations":1,"provenance_completeness":1.0}
    def test_residual_metrics_are_derived_from_real_result(self):
        m=metrics_from_residual_result(self.residual_result()); self.assertTrue(m["task_success"]); self.assertEqual(m["input_tokens"],10)
    def test_residual_measurement_fails_closed_on_missing_counter(self):
        raw=self.residual_result(); raw["metrics"].pop("human_interventions")
        with self.assertRaises(ValueError):
            metrics_from_residual_result(raw)

    def test_residual_measurement_rejects_outcome_override(self):
        with self.assertRaises(ValueError):
            metrics_from_residual_result(
                self.residual_result(),
                overrides={"task_success": False},
            )

    def test_external_measurement_fails_closed_on_missing_counter(self):
        m=self.external_metrics(); m.pop("failed_tool_calls")
        with self.assertRaises(ValueError): metrics_from_external_measurement({"metrics":m,"trace_root":"d"*64})
    def test_execute_trial_binds_residual_trace_and_task(self):
        manifest=self.manifest(); ex=ArmExecution("A",{"provider":"residual","model":"frozen"},"c"*64,lambda _:self.residual_result())
        trial=execute_trial(manifest=manifest,execution=ex,trial_index=1,task_id="task-a",task_payload={"goal":"x"})
        self.assertEqual(trial.trace_root,"d"*64); self.assertEqual(trial.manifest_sha256,manifest.sha256)
    def test_execute_external_preserves_reported_metrics(self):
        manifest=self.manifest(); raw={"trace_root":"e"*64,"metrics":self.external_metrics()}
        ex=ArmExecution("B",{"provider":"moonshot","model":"kimi-frozen"},"c"*64,lambda _:raw)
        trial=execute_trial(manifest=manifest,execution=ex,trial_index=1,task_id="task-b",task_payload={"goal":"x"})
        self.assertEqual(trial.metrics["api_cost_usd"],0.03)

if __name__=="__main__": unittest.main()
