import json
import unittest

from residual.workbench.ax_research import (
    AXExperiment,
    AXResearchBench,
    AXTask,
    AXWorkspace,
    FaultKind,
    Invariant,
)


class AXResearchBenchTests(unittest.TestCase):
    def _baseline(self):
        return AXResearchBench.continuity_baseline(
            experiment_id="AX21-AX-001",
            repo="https://github.com/ninja-ops-guy/residual-agent-harness.git",
            branch="main",
            command=("python", "-m", "residual", "demo"),
            hypothesis="Suspend/resume preserves logical assignment continuity without promoting runtime state to authority.",
        )

    def test_preregistration_is_non_authoritative_and_deterministic(self):
        first = self._baseline()
        second = self._baseline()
        self.assertFalse(first.preregistration()["authority"])
        self.assertEqual(first.canonical_bytes(), second.canonical_bytes())
        self.assertEqual(first.digest(), second.digest())

    def test_ax_documents_are_bounded_to_workspace_and_task(self):
        experiment = self._baseline()
        workspace, task = experiment.ax_documents()
        self.assertEqual(workspace["apiVersion"], "ax.io/v1alpha1")
        self.assertEqual(workspace["kind"], "Workspace")
        self.assertEqual(task["kind"], "Task")
        self.assertEqual(task["spec"]["workspaces"][0]["name"], workspace["metadata"]["name"])
        self.assertNotIn("status", task)
        self.assertNotIn("authority", task)

    def test_rendered_stream_is_json_documents_and_has_no_secrets(self):
        rendered = self._baseline().render_ax_stream()
        docs = [json.loads(part) for part in rendered.strip().split("\n---\n")]
        self.assertEqual([doc["kind"] for doc in docs], ["Workspace", "Task"])
        self.assertNotIn("secretKey", rendered)
        self.assertNotIn("apiKey", rendered)

    def test_recommended_matrix_covers_false_completion_and_continuity(self):
        faults = AXResearchBench.recommended_fault_matrix()
        self.assertIn(FaultKind.FALSE_COMPLETION, {fault.kind for fault in faults})
        self.assertIn(FaultKind.ACTOR_CRASH, {fault.kind for fault in faults})
        self.assertIn(FaultKind.IDENTITY_REBIND, {fault.kind for fault in faults})
        false_completion = next(f for f in faults if f.kind is FaultKind.FALSE_COMPLETION)
        self.assertIs(false_completion.expected_invariant, Invariant.RUNTIME_STATE_IS_NOT_AUTHORITY)

    def test_continuity_campaign_appends_faults_without_mutating_baseline(self):
        baseline = self._baseline()
        campaign = AXResearchBench.continuity_campaign(
            experiment_id="AX21-AX-001",
            repo="https://github.com/ninja-ops-guy/residual-agent-harness.git",
            branch="main",
            command=("python", "-m", "residual", "demo"),
            hypothesis="Suspend/resume preserves logical assignment continuity without promoting runtime state to authority.",
        )
        self.assertEqual(baseline.faults, ())
        self.assertGreaterEqual(len(campaign.faults), 5)

    def test_task_workspace_and_atespace_must_match(self):
        workspace = AXWorkspace(
            name="workspace",
            repo="https://github.com/example/example.git",
            branch="main",
            goal="Prepare.",
            atespace="alpha",
        )
        task = AXTask(
            name="task",
            workspace="workspace",
            command=("true",),
            goal="Run.",
            atespace="beta",
        )
        with self.assertRaisesRegex(ValueError, "same atespace"):
            AXExperiment(
                experiment_id="AX21-MISMATCH",
                hypothesis="Mismatch must fail.",
                workspace=workspace,
                task=task,
                invariants=(Invariant.RUNTIME_STATE_IS_NOT_AUTHORITY,),
            )

    def test_repo_credentials_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "credentials"):
            AXWorkspace(
                name="workspace",
                repo="https://user:token@example.com/repo.git",
                branch="main",
                goal="Prepare.",
            )

    def test_ax_names_follow_rfc1123(self):
        with self.assertRaisesRegex(ValueError, "RFC 1123"):
            AXWorkspace(
                name="Bad_Name",
                repo="https://github.com/example/example.git",
                branch="main",
                goal="Prepare.",
            )

    def test_resource_limits_are_projected(self):
        workspace = AXWorkspace(
            name="workspace",
            repo="https://github.com/example/example.git",
            branch="main",
            goal="Prepare.",
        )
        task = AXTask(
            name="task",
            workspace="workspace",
            command=("python", "agent.py"),
            goal="Run.",
            cpu_request="500m",
            memory_request="1Gi",
            cpu_limit="2",
            memory_limit="4Gi",
        )
        experiment = AXExperiment(
            experiment_id="AX21-RESOURCES",
            hypothesis="Resource requests and limits remain explicit.",
            workspace=workspace,
            task=task,
            invariants=(Invariant.RUNTIME_STATE_IS_NOT_AUTHORITY,),
        )
        _, task_doc = experiment.ax_documents()
        self.assertEqual(task_doc["spec"]["resources"]["requests"]["cpu"], "500m")
        self.assertEqual(task_doc["spec"]["resources"]["limits"]["memory"], "4Gi")


if __name__ == "__main__":
    unittest.main()
