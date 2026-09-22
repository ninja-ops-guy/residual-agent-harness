from __future__ import annotations

import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

from residual.core import canonical
from residual.station.server import Server
from residual.station.service import Station, demo_spec


class AUD1AuthoritySeparationTests(unittest.TestCase):
    """AUD-1 regression 6: coordinator transitions stay usable; workers cannot invoke them."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.station = Station(self.temp.name)
        self.http = Server(("127.0.0.1", 0), self.station, launch_token="authority-separation")
        self.thread = threading.Thread(target=self.http.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.http.server_port}"
        self.operator = self.station.store.settings()["session_token"]

    def tearDown(self):
        self.http.shutdown()
        self.http.server_close()
        self.thread.join()
        self.temp.cleanup()

    def request(self, path, body=None, *, operator=False, worker=None):
        headers = {"Content-Type": "application/json"}
        if operator:
            headers["X-Station-Token"] = self.operator
        if worker is not None:
            headers["Authorization"] = "Bearer " + worker
        req = urllib.request.Request(
            self.url + path,
            data=canonical(body).encode() if body is not None else None,
            headers=headers,
        )
        with urllib.request.urlopen(req) as response:
            raw = response.read()
            return json.loads(raw) if raw else None

    def test_06_coordinator_transition_allowed_worker_transition_denied(self):
        pid = self.station.create(demo_spec(), demo=True)["project_id"]
        self.assertFalse(self.station.store.project(pid)["paused"])

        issued = self.request(
            "/api/workers/access",
            {"enabled": True, "rotate": False},
            operator=True,
        )
        worker = issued["token"]

        # A worker credential cannot cross onto the operator transition surface.
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.request(
                f"/api/projects/{pid}/pause",
                {"paused": True},
                worker=worker,
            )
        self.assertEqual(error.exception.code, 403)
        self.assertFalse(self.station.store.project(pid)["paused"])

        # The same transition remains available to the authenticated coordinator/operator.
        result = self.request(
            f"/api/projects/{pid}/pause",
            {"paused": True},
            operator=True,
        )
        self.assertEqual(result, {"ok": True})
        self.assertTrue(self.station.store.project(pid)["paused"])

        # Prove the coordinator can also reverse the transition.
        self.request(
            f"/api/projects/{pid}/pause",
            {"paused": False},
            operator=True,
        )
        self.assertFalse(self.station.store.project(pid)["paused"])


if __name__ == "__main__":
    unittest.main()
