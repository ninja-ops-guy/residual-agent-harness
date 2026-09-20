from __future__ import annotations

import tempfile
import unittest

from residual.core import ContractError
from residual.station.store import Store
from residual.station.swarm_state import SwarmStateStore, apply_delta, validate_state


def project_state(main_sha="a" * 40, topology_generation=1):
    return {
        "main_sha": main_sha,
        "release_sha": "",
        "release_phase": "dogfood",
        "active_missions": [{"id": "P1", "spec_hash": "evidence:p1"}],
        "blockers": [],
        "readiness_gates": ["AUD-1", "qualification-v1"],
        "accepted_changes": [],
        "retained_failures": [],
        "experiments": [{"id": "AX-21", "state": "active"}],
        "res_up_candidates": [],
        "claim_boundaries": ["model synthesis is advisory"],
        "topology_generation": topology_generation,
        "operator_decisions": [],
        "evidence": ["station:events"],
    }


class SwarmStateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(self.temp.name)
        self.swarm = SwarmStateStore(self.store)

    def tearDown(self):
        self.temp.cleanup()

    def enroll(self, capabilities=None):
        return self.swarm.register_runner(
            "hammer",
            identity_digest="1" * 64,
            host_id="LEGION",
            display_name="Hammer",
            placement="local",
            provider="ollama",
            model="qwen2.5-coder:7b",
            adapter_version="station-v1",
            capabilities=capabilities or {"python": "qualified", "review": "observed"},
        )

    def test_state_is_generation_numbered_hash_bound_and_idempotent(self):
        first = self.swarm.publish(project_state(), {"summary": "baseline"})
        self.assertEqual(first["state_generation"], 1)
        self.assertEqual(validate_state(first), first)

        unchanged = self.swarm.publish(project_state(), {"summary": "baseline"})
        self.assertEqual(unchanged, first)

        second = self.swarm.publish(project_state("b" * 40, 2), {"summary": "advanced"})
        self.assertEqual(second["state_generation"], 2)
        self.assertNotEqual(second["state_hash"], first["state_hash"])

    def test_model_annotations_cannot_shadow_authoritative_truth(self):
        with self.assertRaisesRegex(ContractError, "cannot shadow"):
            self.swarm.publish(project_state(), {"main_sha": "b" * 40})
        with self.assertRaisesRegex(ContractError, "fields mismatch"):
            self.swarm.publish({**project_state(), "model_summary": "ready"})

    def test_state_delta_reaches_exact_target_and_tampering_fails_closed(self):
        first = self.swarm.publish(project_state(), {"summary": "baseline", "drop_me": True})
        target = self.swarm.publish(project_state("b" * 40, 2), {"summary": "next"})
        delta = self.swarm.delta(first["state_generation"])

        self.assertEqual(apply_delta(first, delta), target)

        tampered = dict(delta)
        tampered["authoritative_set"] = {**delta["authoritative_set"], "main_sha": "c" * 40}
        with self.assertRaisesRegex(ContractError, "target hash mismatch"):
            apply_delta(first, tampered)

        wrong_base = dict(delta)
        wrong_base["from_hash"] = "0" * 64
        with self.assertRaisesRegex(ContractError, "does not apply"):
            apply_delta(first, wrong_base)

    def test_runner_must_ack_current_state_before_becoming_eligible(self):
        profile = self.enroll()
        first = self.swarm.publish(project_state())
        self.assertFalse(self.swarm.eligible("hammer"))
        with self.assertRaisesRegex(ContractError, "synchronize"):
            self.swarm.require_current("hammer")

        self.swarm.acknowledge("hammer", first["state_generation"], first["state_hash"], profile["capability_revision"])
        self.assertTrue(self.swarm.eligible("hammer"))
        self.assertEqual(self.swarm.require_current("hammer")["state_hash"], first["state_hash"])

        self.swarm.publish(project_state("b" * 40, 2))
        self.assertFalse(self.swarm.eligible("hammer"))
        with self.assertRaisesRegex(ContractError, "synchronize"):
            self.swarm.require_current("hammer")

    def test_capability_revision_change_invalidates_prior_sync(self):
        original = self.enroll({"python": "advertised"})
        state = self.swarm.publish(project_state())
        self.swarm.acknowledge("hammer", state["state_generation"], state["state_hash"], original["capability_revision"])
        self.assertTrue(self.swarm.eligible("hammer"))
        self.assertFalse(self.swarm.capability_is("hammer", "python", "qualified"))

        changed = self.enroll({"python": "qualified"})
        self.assertNotEqual(changed["capability_revision"], original["capability_revision"])
        self.assertFalse(self.swarm.eligible("hammer"))
        self.assertTrue(self.swarm.capability_is("hammer", "python", "qualified"))
        with self.assertRaisesRegex(ContractError, "capability revision is stale"):
            self.swarm.acknowledge("hammer", state["state_generation"], state["state_hash"], original["capability_revision"])

    def test_runner_identity_cannot_be_rebound(self):
        self.enroll()
        with self.assertRaisesRegex(ContractError, "cannot be rebound"):
            self.swarm.register_runner(
                "hammer",
                identity_digest="2" * 64,
                host_id="DBOX",
                display_name="Not Hammer",
                placement="remote",
            )

    def test_sync_and_enrollment_are_durable_across_restart(self):
        profile = self.enroll()
        state = self.swarm.publish(project_state())
        self.swarm.acknowledge("hammer", state["state_generation"], state["state_hash"], profile["capability_revision"])

        reopened = SwarmStateStore(Store(self.temp.name))
        self.assertTrue(reopened.eligible("hammer"))
        self.assertEqual(reopened.current(), state)
        self.assertEqual(reopened.runner("hammer")["identity_digest"], "1" * 64)

    def test_acknowledgement_requires_exact_state_hash(self):
        profile = self.enroll()
        state = self.swarm.publish(project_state())
        with self.assertRaisesRegex(ContractError, "wrong project-state hash"):
            self.swarm.acknowledge("hammer", state["state_generation"], "0" * 64, profile["capability_revision"])


if __name__ == "__main__":
    unittest.main()
