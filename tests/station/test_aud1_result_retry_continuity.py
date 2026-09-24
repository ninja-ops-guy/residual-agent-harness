"""AUD-1 regression: a result retry must not start after local authority grace expires.

This is a disposable transport fixture only. It does not touch live hosts, R4,
credentials, tunnels, providers, or physical-F6 evidence.
"""
from __future__ import annotations

import time
import unittest

from residual.providers import Reply, Usage
from residual.station.worker import WorkerAuthorityLost, WorkerClient


class ResultRetryContinuityTests(unittest.TestCase):
    def test_result_retry_is_suppressed_after_grace_expires(self):
        client = WorkerClient(
            "http://127.0.0.1:1",
            "fixture",
            heartbeat_interval=0.01,
            heartbeat_grace=0.08,
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
                raise OSError("simulated heartbeat loss")
            if route == "result":
                result_attempts.append(time.monotonic())
                if len(result_attempts) == 1:
                    # The first submission began while authority was still fresh but its
                    # transport failure is not observed until after the local grace window.
                    time.sleep(0.12)
                    raise TimeoutError("simulated stalled result transport")
                return {"task_id": "t-fixture", "state": "review_ready"}
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
            client.run_once("p-fixture", "fixture-runner", Provider())
        self.assertEqual(
            len(result_attempts),
            1,
            "a second result submission began after the continuity grace had expired",
        )


if __name__ == "__main__":
    unittest.main()
