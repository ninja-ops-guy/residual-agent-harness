"""AUD-1 regression: explicit result-authority denial must stop the runner.

Disposable fixture only. No live hosts, credentials, tunnels, providers, or
physical-F6 evidence are touched.
"""
from __future__ import annotations

import urllib.error
import unittest

from residual.providers import Reply, Usage
from residual.station.worker import WorkerAuthorityLost, WorkerClient


class ResultAuthorityDenialTests(unittest.TestCase):
    def test_result_403_surrenders_without_retry_or_empty_fallback(self):
        client = WorkerClient(
            "http://127.0.0.1:1",
            "fixture",
            heartbeat_interval=0.01,
            heartbeat_grace=30,
        )
        result_attempts = []

        def request(route, data):
            if route == "claim":
                return {"work": {
                    "task_id": "t-fixture",
                    "lease": "lease-fixture",
                    "packet": {},
                    "allow_cloud": False,
                }}
            if route == "heartbeat":
                return {"ok": True}
            if route == "result":
                result_attempts.append(data)
                raise urllib.error.HTTPError(
                    client.base + "/api/worker/result", 403,
                    "Task authority belongs to another runner", {}, None,
                )
            raise AssertionError(f"unexpected route: {route}")

        class Provider:
            placement = "local"
            model = "fixture"

            def generate(self, packet, max_tokens):
                return Reply('{"files":{}}', Usage())

            def wire_size(self, packet, max_tokens):
                return 0

        client.request = request
        with self.assertRaises(WorkerAuthorityLost):
            client.run_once("p-fixture", "old-runner", Provider())
        self.assertEqual(
            len(result_attempts),
            1,
            "an explicit authority denial must not be retried or converted into an empty proposal",
        )


if __name__ == "__main__":
    unittest.main()
