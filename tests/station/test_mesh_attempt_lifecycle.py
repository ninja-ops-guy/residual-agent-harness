"""Successor-generation regression: execution authority belongs to a task attempt."""
from __future__ import annotations

import tempfile
import unittest
from unittest.mock import patch

from residual.station.service import Station, demo_spec


class MeshAttemptLifecycleTests(unittest.TestCase):
    def test_expired_admitted_attempt_does_not_poison_next_claim(self):
        with tempfile.TemporaryDirectory() as root:
            station = Station(root)
            pid = station.create(demo_spec(), demo=True)["project_id"]
            station.triage(pid)
            store = station.store
            first = store.claim(pid, "mesh:fixture", "OPS-101", reserve_budget=True)
            self.assertEqual(first["attempt"], 1)
            plan = [{"placement": "local", "model": "fixture/model", "request_bytes": 100}]
            old_budget = store.reserve_mesh_execution(
                pid, first["id"], first["lease"], first["fencing_token"], 1, plan)
            self.assertFalse(old_budget["reconciled"])
            self.assertEqual(store.project(pid)["calls_reserved"], 1)
            # No result/reconciliation. Advance only the lease clock, no sleeps or DB edits.
            with patch("residual.station.store.time.time", return_value=first["lease_until"] + 1):
                store.recover()
            self.assertEqual(store.task(pid, first["id"])["state"], "blocked")
            station.triage(pid)
            second = store.claim(pid, "mesh:fixture", first["id"], reserve_budget=True)
            self.assertEqual(second["attempt"], 2)
            self.assertGreater(second["fencing_token"], first["fencing_token"])
            self.assertNotEqual(second["lease"], first["lease"])
            # First divergence on the unrepaired implementation: this legitimate
            # successor claim still carries attempt 1's unreconciled reservation.
            fresh_budget = store.reserve_mesh_execution(
                pid, second["id"], second["lease"], second["fencing_token"], 1, plan)
            self.assertFalse(fresh_budget["reconciled"])
            # Ambiguous old consumption is never refunded to manufacture capacity.
            self.assertEqual(store.project(pid)["calls_reserved"], 2)


if __name__ == "__main__":
    unittest.main()
