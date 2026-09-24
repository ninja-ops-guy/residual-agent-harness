"""AUD1-C6 regression: worker-access control must have an independent drain bound.

This uses only local threads and an in-memory gate. It does not touch live hosts,
R4/R4.1, credentials, tunnels, providers, canary, or physical F6 evidence.
"""
from __future__ import annotations

import threading
import time
import unittest

from residual.station.worker_access import WorkerAccessGate


class WorkerControlDrainBoundTests(unittest.TestCase):
    def test_control_wait_is_bounded_independently_of_reader_completion(self):
        gate = WorkerAccessGate()

        # The successor repair is expected to honor this per-gate bound. On the
        # current predecessor this attribute is ignored, reproducing C6 safely:
        # the controller remains blocked until the already-admitted reader exits.
        gate.control_timeout = 0.05

        reader_entered = threading.Event()
        release_reader = threading.Event()
        control_finished = threading.Event()
        controller_errors = []

        def reader():
            with gate.operation():
                reader_entered.set()
                release_reader.wait(2)

        def controller():
            try:
                with gate.control():
                    raise AssertionError("timed-out controller unexpectedly entered")
            except Exception as exc:
                controller_errors.append(exc)
            finally:
                control_finished.set()

        reader_thread = threading.Thread(target=reader, daemon=True)
        control_thread = threading.Thread(target=controller, daemon=True)
        reader_thread.start()
        self.assertTrue(reader_entered.wait(1), "fixture reader did not enter")

        started = time.monotonic()
        control_thread.start()
        bounded = control_finished.wait(0.25)
        elapsed = time.monotonic() - started

        # Always release the predecessor reader so the intentionally failing
        # regression cannot strand CI threads.
        release_reader.set()
        reader_thread.join(timeout=1)
        control_thread.join(timeout=1)

        self.assertTrue(
            bounded,
            f"control barrier exceeded independent drain bound; still waiting after {elapsed:.3f}s",
        )
        self.assertTrue(controller_errors, "bounded control must fail explicitly instead of entering")


if __name__ == "__main__":
    unittest.main()
