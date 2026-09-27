import tempfile
import unittest
from pathlib import Path

from residual.research.nested_swarm import (
    TrialRecord,
    build_manifest,
    record_trial,
    summarize_experiment,
    task_corpus_hash,
)


class NestedSwarmResearchTests(unittest.TestCase):
    def manifest(self, trials=1, tasks=None):
        tasks = tasks or {"task-1": "b" * 64}
        return build_manifest(
            registered_at="2026-09-19T13:45:00Z",
            task_corpus_sha256=task_corpus_hash(tasks),
            runtime_revision="test-head",
            trials_per_arm=trials,
            maximum_provider_calls=100,
            maximum_budget_usd=10,
        )

    def metrics(self, success=True):
        return {
            "task_success": success,
            "verifier_pass_rate": 1.0 if success else 0.0,
            "elapsed_ms": 100.0,
            "input_tokens": 10,
            "output_tokens": 5,
            "api_cost_usd": 0.01,
            "provider_calls": 1,
            "retries": 0,
            "evidence_requests": 1,
            "failed_tool_calls": 0,
            "human_interventions": 0,
            "integration_conflicts": 0,
            "duplicate_work_items": 0,
            "convergence_iterations": 1,
            "provenance_completeness": 1.0,
        }

    def trial(self, m, arm, index=1, success=True, task_id="task-1", task_sha="b" * 64):
        return TrialRecord(
            m.sha256,
            arm,
            index,
            task_id,
            task_sha,
            m.runtime_revision,
            {"provider": arm, "model": "frozen"},
            "c" * 64,
            "d" * 64,
            self.metrics(success),
            "pass" if success else "fail",
            None if success else "verification_failed",
        )

    def test_manifest_freezes_four_arms_and_hash(self):
        m = self.manifest()
        self.assertEqual([a.id for a in m.arms], ["A", "B", "C", "D"])
        self.assertEqual(len(m.sha256), 64)

    def test_trial_rejects_nested_credentials(self):
        m = self.manifest()
        with self.assertRaises(ValueError):
            TrialRecord(
                m.sha256,
                "A",
                1,
                "task-1",
                "b" * 64,
                m.runtime_revision,
                {"provider": "A", "session": {"authorization": "Bearer secret"}},
                "c" * 64,
                "d" * 64,
                self.metrics(),
                "pass",
            )

    def test_trial_outcome_must_match_measured_success(self):
        m = self.manifest()
        with self.assertRaisesRegex(ValueError, "outcome"):
            TrialRecord(
                m.sha256,
                "A",
                1,
                "task-1",
                "b" * 64,
                m.runtime_revision,
                {"provider": "A"},
                "c" * 64,
                "d" * 64,
                self.metrics(False),
                "pass",
            )

    def test_report_requires_every_preregistered_task_arm_repeat(self):
        tasks = {"task-1": "b" * 64, "task-2": "e" * 64}
        m = self.manifest(tasks=tasks)

        only_first_task = [self.trial(m, a) for a in "ABCD"]
        with self.assertRaisesRegex(ValueError, "corpus|incomplete"):
            summarize_experiment(m, only_first_task)

        rows = []
        for task_id, task_sha in tasks.items():
            rows.extend(self.trial(m, a, task_id=task_id, task_sha=task_sha) for a in "ABCD")
        report = summarize_experiment(m, rows)
        self.assertEqual(report["arms"]["D"]["outcomes"]["pass"], 2)
        self.assertEqual(len(report["sha256"]), 64)

    def test_failures_are_preserved_as_evidence(self):
        m = self.manifest()
        rows = [self.trial(m, a, success=a != "C") for a in "ABCD"]
        report = summarize_experiment(m, rows)
        self.assertEqual(report["arms"]["C"]["outcomes"]["fail"], 1)

    def test_record_is_hash_bound(self):
        m = self.manifest()
        t = self.trial(m, "A")
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "trial.json"
            record_trial(p, t, output_root=d)
            text = p.read_text()
        self.assertIn(t.sha256, text)
        self.assertNotIn("secret", text)

    def test_record_rejects_escape_from_output_root(self):
        m = self.manifest()
        t = self.trial(m, "A")
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "evidence"
            root.mkdir()
            outside = Path(d) / "outside.json"
            with self.assertRaisesRegex(ValueError, "output_root"):
                record_trial(outside, t, output_root=root)
            with self.assertRaisesRegex(ValueError, "output_root"):
                record_trial(root / ".." / "escape.json", t, output_root=root)


if __name__ == "__main__":
    unittest.main()
