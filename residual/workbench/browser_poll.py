"""Relative polling wait for the browser/WebVM workbench.

The WebVM guest has produced ``OverflowError`` from both ``time.sleep(0.05)``
and ``select.select(..., 0.05)``.  Both CPython wrappers convert the timeout
through ``_PyTime_t`` before entering the guest kernel; the virtual clock can
make that conversion unrepresentable even though a tiny relative wait was
requested.

For this browser-only polling path, call libc ``usleep`` directly with a bounded
relative microsecond interval.  The guest kernel therefore receives a small
relative duration without routing it through CPython's absolute/monotonic time
conversion.  This does not repair or reinterpret clocks and does not alter task,
provider, verifier, or evidence semantics.
"""
from __future__ import annotations

import ctypes
import errno

_libc = ctypes.CDLL(None, use_errno=True)
_usleep = _libc.usleep
_usleep.argtypes = [ctypes.c_uint]
_usleep.restype = ctypes.c_int


def pause(seconds: float = 0.05) -> None:
    """Wait for a small relative interval below CPython's ``_PyTime_t`` layer."""
    if type(seconds) not in (int, float) or not 0 <= seconds <= 1:
        raise ValueError("browser poll interval outside [0, 1]")
    micros = int(seconds * 1_000_000)
    while True:
        ctypes.set_errno(0)
        if _usleep(micros) == 0:
            return
        if ctypes.get_errno() != errno.EINTR:
            raise OSError(ctypes.get_errno(), "browser relative poll wait failed")
