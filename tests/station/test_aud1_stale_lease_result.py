"""AUD-1 regression: an explicit stale-lease result denial must surrender authority.

Disposable real-loopback fixture only. No live hosts, credentials, tunnels,
providers, physical F6, R4/R4.1, canary, or production state are touched.
"""
from __future__ import annotations

import tempfile
import threading
import time
import unittest

from residual.providers import Reply, Usage
from residual.station.server import Server
from residual.station.service import Station, demo_spec
from residual.station.worker import WorkerAuthorityLost, WorkerClient


class StaleLeaseResultTests(unittest.TestCase):
    def test_result_stale_lease_400_surrenders_without_retry_or_empty_fallback(self):
        with tempfile.TemporaryDirectory() as temp:
            station = Station(temp)
            project = station.create(demo_spec(), demo=True)["project_id"]
            station.triage(project)
            http = Server(("127.0.0.1", 0), station, launch_token="stale-lease-fixture")
            thread = threading.Thread(target=http.serve_forever, daemon=True)
            thread.start()
            try:
                token = http.configure_worker_access(True, False)["token"]
                client = WorkerClient(
                    f"http://127.0.0.1:{http.server_port}",
                    token,
                    heartbeat_interval=10,
                    heartbeat_grace=30,
                )
                result_attempts = []
                request = client.request

                def observed_request(route, data):
                    if route == "result":
                        result_attempts.append(data)
                    return request(route, data)

                client.request = observed_request

                class Provider:
                    placement = "local"
                    model = "fixture"

                    def generate(self, packet, max_tokens):
                        # Keep the same server-side owner but expire its authoritative
                        # lease before submission. The Station answers result with
                        # HTTP 400 {"error":"Stale task lease"}.
                        with station.store.transaction() as connection:
                            task = station.store._task(connection, project, "OPS-101")
                            task["lease_until"] = time.time() - 1
                            station.store._write_task(connection, project, task)
                        return Reply('{"files":{}}', Usage())

                    def wire_size(self, packet, max_tokens):
                        return 0

                with self.assertRaises(WorkerAuthorityLost):
                    client.run_once(project, "old-runner", Provider())
                self.assertEqual(
                    len(result_attempts),
                    1,
                    "a stale authoritative lease denial must not be retried or converted into an empty proposal",
                )
            finally:
                http.shutdown()
                http.server_close()
                thread.join(timeout=3)


if __name__ == "__main__":
    unittest.main()
