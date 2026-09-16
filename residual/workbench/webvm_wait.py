"""Bounded wait primitive for long-lived WebVM guest interpreters.

Published WebVM diagnostics on the pinned i386 guest reproduce a process-local
CPython ``time.sleep(positive_duration)`` failure on call 273.  Direct libc
``nanosleep`` does not reproduce that bounded symptom.  Long-lived browser-only
poll/retry loops therefore use this narrow POSIX wait instead of ``time.sleep``.

This helper is deliberately small and fail-closed.  It does not silently fall
back to Python ``time.sleep`` when libc ``nanosleep`` is unavailable.
"""
from __future__ import annotations

import ctypes
import errno
from functools import lru_cache
import math
import os

_NSEC_PER_SEC = 1_000_000_000
_MAX_WAIT_SECONDS = 5.0


class _Timespec(ctypes.Structure):
    _fields_ = [("tv_sec", ctypes.c_long), ("tv_nsec", ctypes.c_long)]


@lru_cache(maxsize=1)
def _nanosleep_function():
    if os.name != "posix":
        raise RuntimeError("WebVM browser wait requires POSIX nanosleep")
    libc = ctypes.CDLL(None, use_errno=True)
    try:
        function = libc.nanosleep
    except AttributeError as exc:
        raise RuntimeError("WebVM browser wait nanosleep is unavailable") from exc
    function.argtypes = [ctypes.POINTER(_Timespec), ctypes.POINTER(_Timespec)]
    function.restype = ctypes.c_int
    return function


def wait(seconds: float) -> None:
    """Wait for a small positive duration using libc ``nanosleep``.

    EINTR resumes only the unconsumed remainder.  Other libc failures are
    surfaced rather than converted into a reusable transport outcome.
    """
    if isinstance(seconds, bool) or not isinstance(seconds, (int, float)):
        raise TypeError("wait duration must be numeric")
    seconds = float(seconds)
    if not math.isfinite(seconds) or seconds < 0 or seconds > _MAX_WAIT_SECONDS:
        raise ValueError("wait duration outside WebVM browser bounds")
    if seconds == 0:
        return

    total_ns = int(round(seconds * _NSEC_PER_SEC))
    if total_ns <= 0:
        return
    sec, nsec = divmod(total_ns, _NSEC_PER_SEC)
    request = _Timespec(sec, nsec)
    function = _nanosleep_function()

    while True:
        remaining = _Timespec()
        ctypes.set_errno(0)
        rc = int(function(ctypes.byref(request), ctypes.byref(remaining)))
        if rc == 0:
            return
        error = ctypes.get_errno()
        if error == errno.EINTR:
            if remaining.tv_sec < 0 or not 0 <= remaining.tv_nsec < _NSEC_PER_SEC:
                raise RuntimeError("nanosleep returned an invalid remainder")
            if remaining.tv_sec == 0 and remaining.tv_nsec == 0:
                return
            request = remaining
            continue
        raise OSError(error, os.strerror(error))
