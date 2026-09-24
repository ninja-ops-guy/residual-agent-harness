"""Single-Station worker admission barrier; it is not an identity provider.

Worker operations may run concurrently. Credential/access-control changes wait
for admitted operations to drain and prevent new admissions until the change
commits. A completed rotation/disable therefore cannot be followed by a delayed
request using the old authorization snapshot. Control-plane drain itself is
bounded: if admitted work does not drain by the deadline, the control attempt
fails before any credential/access mutation and normal admission can resume.
"""
from __future__ import annotations

from contextlib import contextmanager
import math
import threading
import time


DEFAULT_CONTROL_DRAIN_TIMEOUT = 600.0


class WorkerControlDrainTimeout(TimeoutError):
    """Exclusive worker-access control could not be acquired before its deadline."""


class WorkerAccessGate:
    """Writer-preferred shared/exclusive admission, scoped to one server process.

    Do not acquire this gate while holding Station project/store locks. Control
    and operation contexts are deliberately non-reentrant; never nest them.
    """

    def __init__(self, control_timeout=DEFAULT_CONTROL_DRAIN_TIMEOUT):
        self.control_timeout = self._validated_timeout(control_timeout)
        self._condition = threading.Condition()
        self._readers = 0
        self._writers_waiting = 0
        self._writing = False

    @staticmethod
    def _validated_timeout(value):
        if type(value) not in {int, float} or not math.isfinite(value) or value <= 0:
            raise ValueError("worker control drain timeout must be a positive finite number")
        return float(value)

    @contextmanager
    def operation(self):
        with self._condition:
            self._condition.wait_for(lambda: not self._writing and not self._writers_waiting)
            self._readers += 1
        try:
            yield
        finally:
            with self._condition:
                self._readers -= 1
                self._condition.notify_all()

    @contextmanager
    def control(self):
        timeout = self._validated_timeout(self.control_timeout)
        with self._condition:
            self._writers_waiting += 1
            self._condition.notify_all()
            try:
                deadline = time.monotonic() + timeout
                while self._writing or self._readers != 0:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise WorkerControlDrainTimeout(
                            "Worker access control drain timed out before exclusive admission; "
                            "no access change was applied"
                        )
                    self._condition.wait(timeout=remaining)
                self._writing = True
            finally:
                self._writers_waiting -= 1
                self._condition.notify_all()
        try:
            yield
        finally:
            with self._condition:
                self._writing = False
                self._condition.notify_all()
