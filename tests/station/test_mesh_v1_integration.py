"""Bounded main + #404/#493 integration; synthetic providers, loopback only.

Reuses the existing real HTTP/Station fixture without inheriting its test cases.
No native-host, independent-provider, or release qualification is implied.
"""
import unittest
import urllib.error
from unittest.mock import patch

from ai_providers import ProviderError
from residual.core import ContractError
from residual.station.continuity import ContinuityProvider
from residual.station.contracts import sha
from residual.station.mesh_worker import MeshAdmissionRejected
from residual.station.service import DEMO_FILES, Station
from tests.station import test_mesh_budget_boundaries as boundaries
from tests.station.test_sc_mesh_continuity import FakeProvider


class MeshV1IntegrationTests(unittest.TestCase):
    setUp = boundaries.HTTPBoundaryTests.setUp
    tearDown = boundaries.HTTPBoundaryTests.tearDown

    def test_restart_successor_binds_budget_and_result_evidence(self):
        first = self.client.claim(self.pid, "OPS-101")
        old = self.client.execution_admit(first, boundaries.PLAN)["budget"]
        # Real startup recovery, same durable SQLite root; no lease renewal.
        reopened = Station(self.temp.name)
        self.assertEqual(reopened.store.task(self.pid, "OPS-101")["state"], "blocked")
        self.station.triage(self.pid)
        self.client.sync(self.pid)
        second = self.client.claim(self.pid, "OPS-101")
        budget = self.client.execution_admit(second, boundaries.PLAN)["budget"]
        self.assertEqual(second["attempt"], first["attempt"] + 1)
        self.assertGreater(second["fencing_token"], first["fencing_token"])
        for key in ("attempt", "generation", "fencing_token"):
            self.assertEqual(budget[key], second[key])
        before = self.station.store.project(self.pid)
        with self.assertRaises(MeshAdmissionRejected):
            self.client.execution_admit(first, boundaries.PLAN)
        with self.assertRaises(urllib.error.HTTPError):
            self.client.submit_result(first, submission_id="stale-result",
                                      response={"files": {}}, provider_attempts=[])
        self.assertEqual(self.station.store.project(self.pid), before)
        response = {"files": DEMO_FILES["OPS-101"]}
        result = self.client.submit_result(second, submission_id="successor-result",
            response=response, provider_attempts=boundaries.OBSERVED)
        self.assertEqual(result["state"], "review_ready")
        events = self.station.store.events(self.pid)
        archived = [e for e in events if e["event_type"] == "mesh.execution.fenced"]
        self.assertEqual(len(archived), 1)
        self.assertEqual(archived[0]["data"]["budget"], old)
        submitted = [e for e in events if e["event_type"] == "mesh.result.submitted"]
        self.assertEqual(len(submitted), 1)
        evidence = submitted[0]["data"]
        for key in ("attempt", "generation", "fencing_token", "task_id"):
            self.assertEqual(evidence[key], second[key])
        self.assertEqual(evidence["worker_id"], "claw-a")
        self.assertEqual(evidence["response_digest"], sha(response))
        self.assertEqual(evidence["provider_attempts"], boundaries.OBSERVED)
        # Ambiguous attempt 1 remains charged; only observed bytes of attempt 2 refund.
        project = self.station.store.project(self.pid)
        self.assertEqual(project["calls_reserved"], 2)
        self.assertEqual(project["request_bytes_reserved"], 190)

    def test_revocation_after_admission_prevents_result_and_refund(self):
        work = self.client.claim(self.pid, "OPS-101")
        self.client.execution_admit(work, boundaries.PLAN)
        before = self.station.store.project(self.pid)
        self.station.mesh.revoke("claw-a")
        with self.assertRaises(urllib.error.HTTPError):
            self.client.submit_result(work, submission_id="revoked", response={"files": {}},
                                      provider_attempts=[])
        self.assertEqual(self.station.store.project(self.pid), before)
        self.assertFalse(self.station.store.task(self.pid, "OPS-101")["mesh_execution_budget"]["reconciled"])
        self.assertFalse(any(e["event_type"] == "mesh.result.submitted"
                             for e in self.station.store.events(self.pid)))

    def test_worker_capability_rejection_does_not_consume_assignment(self):
        work = self.client.claim(self.pid, "OPS-101")
        before = self.station.store.project(self.pid)
        with self.assertRaises(MeshAdmissionRejected) as caught:
            self.client.execution_admit(work, [{**boundaries.PLAN[0], "placement": "remote"}])
        self.assertEqual(caught.exception.reason_code, "WORKER_CAPABILITY_DENIED")
        self.assertEqual(self.station.store.project(self.pid), before)
        self.assertTrue(self.client.execution_admit(work, boundaries.PLAN)["admitted"])

    def test_generation_change_rejects_result_without_reconciliation(self):
        work = self.client.claim(self.pid, "OPS-101")
        self.client.execution_admit(work, boundaries.PLAN)
        self.station.store.advance_generation(self.pid, "fixture generation rotation")
        before = self.station.store.project(self.pid)
        with self.assertRaises(urllib.error.HTTPError):
            self.client.submit_result(work, submission_id="old-generation",
                                      response={"files": {}}, provider_attempts=[])
        self.assertEqual(self.station.store.project(self.pid), before)
        self.assertFalse(self.station.store.task(self.pid, "OPS-101")["mesh_execution_budget"]["reconciled"])

    def test_continuity_callback_fences_fallback_after_lease_expiry(self):
        # This verifies the existing callback boundary, not production #489 wiring.
        work = self.client.claim(self.pid, "OPS-101")
        first = FakeProvider("primary", "local", "http://127.0.0.1:1", [
            ProviderError(provider="primary", code="connection", retryable=True)])
        fallback = FakeProvider("fallback", "local", "http://127.0.0.1:2", [object()])
        checks = []
        def before(provider, packet, cap):
            checks.append(provider.kind)
            self.client.admit_provider_attempt(work, placement="local", request_bytes=100)
        def after(provider, attempt, reply, error):
            task = self.station.store.task(self.pid, "OPS-101")
            with patch("residual.station.store.time.time", return_value=task["lease_until"] + 1):
                self.station.store.recover()
        with self.assertRaises(urllib.error.HTTPError):
            ContinuityProvider([first, fallback]).generate({}, 10, "local",
                before_attempt=before, after_attempt=after)
        self.assertEqual(checks, ["primary", "fallback"])
        self.assertEqual((first.calls, fallback.calls), (1, 0))
        self.assertEqual(self.station.store.project(self.pid)["calls_reserved"], 1)


if __name__ == "__main__":
    unittest.main()
