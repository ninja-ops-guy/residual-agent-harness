import unittest

from residual.control_plane.acceleration import (
    AccelerationConductor,
    DerivedStatus,
    PortfolioManifest,
    SCHEMA_VERSION,
)
from residual.core import ContractError, digest


def manifest(*, release_freeze=True, tasks=None):
    return {
        "schema_version": SCHEMA_VERSION,
        "release_freeze": release_freeze,
        "lanes": [
            {"id": "v1", "title": "v1 convergence", "benefit": "Ship a stable release"},
            {"id": "slm", "title": "SLM research", "benefit": "Reduce cost and latency"},
        ],
        "tasks": tasks or [
            {
                "id": "qualify",
                "lane": "v1",
                "scope": "required",
                "state": "complete",
                "depends_on": [],
                "preparable": False,
                "summary": "Qualify release",
            },
            {
                "id": "release",
                "lane": "v1",
                "scope": "required",
                "state": "human_gate",
                "depends_on": ["qualify"],
                "preparable": False,
                "summary": "Authorize release",
                "owner_action": {
                    "summary": "Attest exact release candidate",
                    "approval_text": "RESIDUAL-MAINTAINER-APPROVAL: abc123",
                    "evidence_digest": digest({"release": "candidate"}),
                    "risk_class": "A",
                    "checks_passed": True,
                    "independent_review_passed": True,
                    "unresolved_findings": 0,
                },
            },
            {
                "id": "slm-00",
                "lane": "slm",
                "scope": "research",
                "state": "pending",
                "depends_on": ["release"],
                "preparable": True,
                "summary": "Freeze SLM benchmark",
            },
        ],
    }


class AccelerationControlPlaneTests(unittest.TestCase):
    def test_owner_queue_is_exact_and_fail_closed(self):
        conductor = AccelerationConductor(PortfolioManifest.from_dict(manifest()))
        self.assertEqual(conductor.status_for("release"), DerivedStatus.OWNER_READY)
        queue = conductor.owner_queue()
        self.assertEqual(len(queue), 1)
        self.assertEqual(queue[0]["task_id"], "release")
        self.assertEqual(queue[0]["approval_text"], "RESIDUAL-MAINTAINER-APPROVAL: abc123")

        value = manifest()
        value["tasks"][1]["owner_action"]["unresolved_findings"] = 1
        blocked = AccelerationConductor(PortfolioManifest.from_dict(value))
        self.assertEqual(blocked.status_for("release"), DerivedStatus.OWNER_BLOCKED)
        self.assertEqual(blocked.owner_queue(), [])

    def test_release_freeze_blocks_research_execution_but_allows_prep(self):
        value = manifest()
        value["tasks"][1]["state"] = "complete"
        value["tasks"][1].pop("owner_action")
        conductor = AccelerationConductor(PortfolioManifest.from_dict(value))
        self.assertEqual(conductor.status_for("slm-00"), DerivedStatus.PREP_READY)
        ready = conductor.ready_work()
        self.assertEqual(ready["execute"], [])
        self.assertEqual([item["task_id"] for item in ready["prepare"]], ["slm-00"])

    def test_unfreezing_promotes_completed_dependency_to_execution_ready(self):
        value = manifest(release_freeze=False)
        value["tasks"][1]["state"] = "complete"
        value["tasks"][1].pop("owner_action")
        conductor = AccelerationConductor(PortfolioManifest.from_dict(value))
        self.assertEqual(conductor.status_for("slm-00"), DerivedStatus.READY)
        self.assertEqual([item["task_id"] for item in conductor.ready_work()["execute"]], ["slm-00"])

    def test_human_gate_never_auto_crosses(self):
        conductor = AccelerationConductor(PortfolioManifest.from_dict(manifest()))
        self.assertNotIn("release", [item["task_id"] for item in conductor.ready_work()["execute"]])
        self.assertEqual(conductor.status_for("release"), DerivedStatus.OWNER_READY)

    def test_dependency_cycle_is_rejected(self):
        tasks = [
            {
                "id": "a", "lane": "v1", "scope": "required", "state": "pending",
                "depends_on": ["b"], "preparable": False, "summary": "a",
            },
            {
                "id": "b", "lane": "v1", "scope": "required", "state": "pending",
                "depends_on": ["a"], "preparable": False, "summary": "b",
            },
        ]
        with self.assertRaises(ContractError):
            PortfolioManifest.from_dict(manifest(tasks=tasks))

    def test_running_nonrequired_work_is_rejected_while_release_frozen(self):
        tasks = [
            {
                "id": "research", "lane": "slm", "scope": "research", "state": "running",
                "depends_on": [], "preparable": True, "summary": "research",
            }
        ]
        with self.assertRaises(ContractError):
            PortfolioManifest.from_dict(manifest(tasks=tasks))

    def test_snapshot_is_deterministic_and_binds_manifest(self):
        conductor = AccelerationConductor(PortfolioManifest.from_dict(manifest()))
        one = conductor.snapshot()
        two = conductor.snapshot()
        self.assertEqual(one, two)
        self.assertEqual(one["manifest_hash"], conductor.manifest.manifest_hash)
        self.assertEqual(one["snapshot_hash"], digest({k: v for k, v in one.items() if k != "snapshot_hash"}))


if __name__ == "__main__":
    unittest.main()
