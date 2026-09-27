"""Single-Station worker admission barrier; it is not an identity provider.

Worker operations may run concurrently. Credential/access-control changes wait
for admitted operations to drain and prevent new admissions until the change
commits. A completed rotation/disable therefore cannot be followed by a delayed
request using the old authorization snapshot. Callers MUST re-read credentials
inside operation(), after reading the HTTP body and before doing any work.
"""
from __future__ import annotations

from contextlib import contextmanager
import threading


class WorkerAccessGate:
    """Writer-preferred shared/exclusive admission, scoped to one server process.

    Do not acquire this gate while holding Station project/store locks. Control
    and operation contexts are deliberately non-reentrant; never nest them.
    """

    def __init__(self):
        self._condition = threading.Condition()
        self._readers = 0
        self._writers_waiting = 0
        self._writing = False

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
        with self._condition:
            self._writers_waiting += 1
            self._condition.notify_all()
            try:
                self._condition.wait_for(lambda: not self._writing and self._readers == 0)
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
