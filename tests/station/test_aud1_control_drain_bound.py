"""AUD1-C6 regression: worker-access control must have an independent drain bound.

Local threads and loopback HTTP only. No live hosts, R4/R4.1, credentials,
tunnels, providers, canary, or physical F6 evidence are touched.
"""
from __future__ import annotations

import json
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request

from residual.core import canonical
from residual.station.server import Server
from residual.station.service import Station
from residual.station.worker_access import WorkerAccessGate, WorkerControlDrainTimeout


class WorkerControlDrainBoundTests(unittest.TestCase):
    def held_reader(self, gate):
        entered = threading.Event()
        release = threading.Event()

        def reader():
            with gate.operation():
                entered.set()
                release.wait(2)

        thread = threading.Thread(target=reader, daemon=True)
        thread.start()
        self.assertTrue(entered.wait(1), "fixture reader did not enter")
        return release, thread

    def test_control_wait_is_bounded_independently_of_reader_completion(self):
        gate = WorkerAccessGate(control_timeout=0.05)
        release_reader, reader_thread = self.held_reader(gate)
        control_finished = threading.Event()
        controller_errors = []
        entered_control = threading.Event()

        def controller():
            try:
                with gate.control():
                    entered_control.set()
            except Exception as exc:
                controller_errors.append(exc)
            finally:
                control_finished.set()

        control_thread = threading.Thread(target=controller, daemon=True)
        started = time.monotonic()
        control_thread.start()
        bounded = control_finished.wait(0.25)
        elapsed = time.monotonic() - started

        try:
            self.assertTrue(
                bounded,
                f"control barrier exceeded independent drain bound; still waiting after {elapsed:.3f}s",
            )
            self.assertFalse(entered_control.is_set(), "timed-out control unexpectedly entered")
            self.assertEqual(len(controller_errors), 1)
            self.assertIsInstance(controller_errors[0], WorkerControlDrainTimeout)
            with gate._condition:
                self.assertEqual(gate._writers_waiting, 0)
                self.assertFalse(gate._writing)
        finally:
            release_reader.set()
            reader_thread.join(timeout=1)
            control_thread.join(timeout=1)

    def test_timeout_releases_writer_preference_for_new_operations(self):
        gate = WorkerAccessGate(control_timeout=0.05)
        release_reader, reader_thread = self.held_reader(gate)
        timed_out = threading.Event()

        def controller():
            try:
                with gate.control():
                    raise AssertionError("timed-out controller unexpectedly entered")
            except WorkerControlDrainTimeout:
                timed_out.set()

        control_thread = threading.Thread(target=controller, daemon=True)
        control_thread.start()
        self.assertTrue(timed_out.wait(0.25), "control did not time out")

        later_entered = threading.Event()

        def later_reader():
            with gate.operation():
                later_entered.set()

        later_thread = threading.Thread(target=later_reader, daemon=True)
        later_thread.start()
        try:
            self.assertTrue(
                later_entered.wait(0.25),
                "timed-out writer left writer-preference state stuck",
            )
        finally:
            release_reader.set()
            reader_thread.join(timeout=1)
            control_thread.join(timeout=1)
            later_thread.join(timeout=1)

    def test_rotation_timeout_is_503_and_does_not_partially_mutate_credentials(self):
        with tempfile.TemporaryDirectory() as temp:
            station = Station(temp)
            server = Server(("127.0.0.1", 0), station)
            server._worker_gate.control_timeout = 0.05
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            url = f"http://127.0.0.1:{server.server_port}"
            operator = station.store.settings()["session_token"]

            def post(body):
                request = urllib.request.Request(
                    url + "/api/workers/access",
                    data=canonical(body).encode(),
                    headers={
                        "Content-Type": "application/json",
                        "X-Station-Token": operator,
                    },
                )
                with urllib.request.urlopen(request, timeout=2) as response:
                    return json.loads(response.read())

            try:
                enabled = post({"enabled": True, "rotate": False})
                self.assertTrue(enabled["enabled"])
                before = station.store.settings()
                release_reader, reader_thread = self.held_reader(server._worker_gate)
                try:
                    with self.assertRaises(urllib.error.HTTPError) as error:
                        post({"enabled": True, "rotate": True})
                    self.assertEqual(error.exception.code, 503)
                    payload = json.loads(error.exception.read())
                    self.assertIn("drain timed out", payload["error"])
                    after = station.store.settings()
                    self.assertEqual(after["remote_workers_enabled"], before["remote_workers_enabled"])
                    self.assertEqual(after["worker_token"], before["worker_token"])
                    self.assertEqual(after["worker_credentials"], before["worker_credentials"])
                finally:
                    release_reader.set()
                    reader_thread.join(timeout=1)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

    def test_timeout_configuration_rejects_unbounded_values(self):
        for value in (0, -1, float("inf"), float("nan"), True, "600"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    WorkerAccessGate(control_timeout=value)


if __name__ == "__main__":
    unittest.main()
