from __future__ import annotations

import json
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from residual.core import ContractError, canonical
from residual.station.mesh import MeshEnvelope, new_envelope, payload_digest
from residual.station.mesh_outbox import MeshOutbox
from residual.station.server import Server
from residual.station.service import Station, demo_spec


def enrollment(pid, worker="claw-a", capabilities=None, topics=None):
    return {
        "worker_id": worker,
        "host_id": "host-a",
        "adapter": "openclaw",
        "adapter_version": "2026.6.1",
        "project_ids": [pid],
        "capabilities": capabilities or ["model.local", "files.propose", "evidence.submit", "comms.read", "comms.write"],
        "topics": topics or ["ops"],
        "expires_at": time.time() + 3600,
    }


class MeshContractTests(unittest.TestCase):
    def test_non_task_message_cannot_smuggle_authority(self):
        raw = new_envelope(project_id="p-1", sender="w", recipient="all", kind="message",
                           generation=1, payload={"text": "hello"})
        raw["task_id"] = "T-1"
        with self.assertRaises(ContractError):
            MeshEnvelope.parse(raw)

    def test_task_message_requires_complete_authority_binding(self):
        raw = new_envelope(project_id="p-1", sender="w", recipient="all", kind="message",
                           generation=1, payload={"text": "hello"})
        raw["kind"] = "task.note"
        with self.assertRaises(ContractError):
            MeshEnvelope.parse(raw)

    def test_payload_digest_and_ttl_are_enforced(self):
        raw = new_envelope(project_id="p-1", sender="w", recipient="all", kind="message",
                           generation=1, payload={"text": "hello"})
        raw["payload_digest"] = "0" * 64
        with self.assertRaises(ContractError):
            MeshEnvelope.parse(raw)
        raw = new_envelope(project_id="p-1", sender="w", recipient="all", kind="message",
                           generation=1, payload={"text": "hello"})
        raw["expires_at"] = raw["created_at"] + 4000
        raw["payload_digest"] = payload_digest(raw["payload"])
        with self.assertRaises(ContractError):
            MeshEnvelope.parse(raw)


class MeshStateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.station = Station(self.temp.name)
        self.pid = self.station.create(demo_spec(), demo=True)["project_id"]
        self.station.triage(self.pid)

    def tearDown(self):
        self.temp.cleanup()

    def _enroll(self, worker="claw-a", capabilities=None):
        result = self.station.mesh.enroll(
            enrollment(self.pid, worker, capabilities),
            allowed_capabilities=self.station.store.settings()["mesh_allowed_capabilities"],
        )
        auth = self.station.mesh.authenticate(result["token"])
        return result, auth

    def test_enrollment_token_is_hashed_and_wrong_project_denied(self):
        result, worker = self._enroll()
        token = result["token"]
        with self.station.store.connect() as c:
            row = c.execute("SELECT token_hash,value FROM mesh_workers WHERE worker_id=?", ("claw-a",)).fetchone()
        self.assertNotIn(token, row["value"])
        self.assertNotEqual(row["token_hash"], token)
        with self.assertRaises(ContractError):
            self.station.mesh.snapshot(worker, "p-wrong")

    def test_sync_is_required_and_generation_advance_forces_resync(self):
        _, worker = self._enroll()
        msg = new_envelope(project_id=self.pid, sender="claw-a", recipient="all", kind="message",
                           generation=1, payload={"text": "hello"})
        with self.assertRaises(ContractError):
            self.station.mesh.admit_message(worker, msg)
        self.station.mesh.begin_sync(worker)
        snap = self.station.mesh.snapshot(worker, self.pid)
        self.assertEqual(snap["generation"], 1)
        worker = self.station.mesh.authenticate(
            # look up token through fresh enrollment in a separate worker instead of storing plaintext
            self.station.mesh.enroll(enrollment(self.pid, "claw-b"),
                                     allowed_capabilities=self.station.store.settings()["mesh_allowed_capabilities"])["token"]
        )
        self.station.mesh.begin_sync(worker)
        self.station.mesh.snapshot(worker, self.pid)
        self.station.store.advance_generation(self.pid, "test generation change")
        stale = new_envelope(project_id=self.pid, sender="claw-b", recipient="all", kind="message",
                             generation=1, payload={"text": "stale"})
        with self.assertRaises(ContractError):
            self.station.mesh.admit_message(worker, stale)

    def test_idempotent_admission_same_bytes_and_conflict(self):
        result, worker = self._enroll()
        self.station.mesh.begin_sync(worker)
        self.station.mesh.snapshot(worker, self.pid)
        worker = self.station.mesh.authenticate(result["token"])
        msg = new_envelope(project_id=self.pid, sender="claw-a", recipient="all", kind="message",
                           generation=1, payload={"text": "hello"}, idempotency_key="same-op")
        first = self.station.mesh.admit_message(worker, msg)
        second = self.station.mesh.admit_message(worker, msg)
        self.assertEqual(first["seq"], second["seq"])
        self.assertTrue(second["duplicate"])
        other = dict(msg)
        other["message_id"] = "different"
        other["payload"] = {"text": "changed"}
        other["payload_digest"] = payload_digest(other["payload"])
        with self.assertRaises(ContractError):
            self.station.mesh.admit_message(worker, other)

    def test_revocation_survives_store_reopen(self):
        result, worker = self._enroll()
        self.station.mesh.revoke(worker["worker_id"])
        reopened = Station(self.temp.name)
        with self.assertRaises(ContractError):
            reopened.mesh.authenticate(result["token"])

    def test_task_scoped_message_binds_lease_attempt_and_fence(self):
        result, worker = self._enroll()
        self.station.mesh.begin_sync(worker)
        self.station.mesh.snapshot(worker, self.pid)
        worker = self.station.mesh.authenticate(result["token"])
        work = self.station.prepare(self.pid, "mesh:claw-a", "OPS-101",
                                    routes={"local"}, capabilities=set(worker["capabilities"]))
        t = work["task"]
        valid = new_envelope(
            project_id=self.pid, sender="claw-a", recipient="topic:ops", kind="task.note",
            generation=1, payload={"text": "working"}, task_id=t["id"], attempt=t["attempt"],
            lease_id=work["lease"], fencing_token=t["fencing_token"],
        )
        self.station.mesh.admit_message(worker, valid)
        stale = dict(valid)
        stale["message_id"] = "stale-fence"
        stale["idempotency_key"] = "stale-fence"
        stale["fencing_token"] -= 1
        with self.assertRaises(ContractError):
            self.station.mesh.admit_message(worker, stale)

    def test_presence_heartbeat_does_not_extend_execution_lease(self):
        result, worker = self._enroll()
        self.station.mesh.begin_sync(worker)
        self.station.mesh.snapshot(worker, self.pid)
        worker = self.station.mesh.authenticate(result["token"])
        work = self.station.prepare(self.pid, "mesh:claw-a", "OPS-101",
                                    routes={"local"}, capabilities=set(worker["capabilities"]))
        before = self.station.store.task(self.pid, "OPS-101")["lease_until"]
        self.station.store.heartbeat(self.pid, "OPS-101", work["lease"],
                                     work["task"]["fencing_token"], renew=False)
        self.station.mesh.presence(worker, project_id=self.pid)
        after = self.station.store.task(self.pid, "OPS-101")["lease_until"]
        self.assertEqual(before, after)

    def test_mesh_stop_revokes_mesh_lease_and_prevents_new_claims(self):
        result, worker = self._enroll()
        self.station.mesh.begin_sync(worker)
        self.station.mesh.snapshot(worker, self.pid)
        worker = self.station.mesh.authenticate(result["token"])
        self.station.prepare(self.pid, "mesh:claw-a", "OPS-101",
                             routes={"local"}, capabilities=set(worker["capabilities"]))
        stopped = self.station.store.mesh_stop(self.pid)
        self.assertTrue(stopped["revoked_leases"])
        self.assertEqual(self.station.store.task(self.pid, "OPS-101")["state"], "blocked")
        self.assertIsNone(self.station.store.claim(self.pid, "mesh:claw-a", routes={"local"},
                                                   capabilities=set(worker["capabilities"])))


class MeshOutboxTests(unittest.TestCase):
    def test_outbox_is_durable_conflict_safe_and_inbox_deduplicates(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "mesh.sqlite3"
            one = MeshOutbox(path)
            value = {"schema": "example", "n": 1}
            one.enqueue("op-1", value)
            two = MeshOutbox(path)
            self.assertEqual(two.due()[0]["value"], value)
            with self.assertRaises(ContractError):
                two.enqueue("op-1", {"schema": "example", "n": 2})
            two.ack("op-1", {"seq": 7})
            self.assertEqual(two.pending(), 0)
            applied = []
            self.assertTrue(two.apply_inbox("p-1", 7, value, lambda c: applied.append(1)))
            self.assertFalse(two.apply_inbox("p-1", 7, value, lambda c: applied.append(2)))
            self.assertEqual(applied, [1])
            self.assertEqual(two.cursor("p-1"), 7)


class MeshHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.station = Station(self.temp.name)
        self.pid = self.station.create(demo_spec(), demo=True)["project_id"]
        self.station.triage(self.pid)
        self.http = Server(("127.0.0.1", 0), self.station)
        self.thread = threading.Thread(target=self.http.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.http.server_port}"
        self.session = self.station.store.settings()["session_token"]

    def tearDown(self):
        self.http.shutdown()
        self.http.server_close()
        self.thread.join(timeout=2)
        self.temp.cleanup()

    def request(self, path, body=None, *, mesh_token=None, session=False):
        headers = {"Content-Type": "application/json"}
        if mesh_token:
            headers["Authorization"] = "Bearer " + mesh_token
        if session:
            headers["X-Station-Token"] = self.session
        req = urllib.request.Request(self.url + path,
            data=canonical(body).encode() if body is not None else None, headers=headers)
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read())

    def test_owner_enrollment_worker_sync_and_message_round_trip(self):
        created = self.request("/api/mesh/enroll", enrollment(self.pid), session=True)
        token = created["token"]
        snap = self.request(f"/api/mesh/worker/sync?project_id={self.pid}", mesh_token=token)["snapshot"]
        msg = new_envelope(project_id=self.pid, sender="claw-a", recipient="all", kind="message",
                           generation=snap["generation"], payload={"text": "hello"},
                           idempotency_key="http-op")
        receipt = self.request("/api/mesh/worker/message", msg, mesh_token=token)
        self.assertGreater(receipt["seq"], 0)
        replay = self.request(f"/api/mesh/worker/messages?project_id={self.pid}&after=0", mesh_token=token)
        self.assertEqual(replay["messages"][0]["envelope"]["payload"], {"text": "hello"})


if __name__ == "__main__":
    unittest.main()
