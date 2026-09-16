"""WebVM-specific polling wait backend.

The deployed i386 WebVM runtime has a retained defect in the positive-duration
``time.sleep``/time64 wait path.  Normal environments keep using Python's
standard sleep.  The WebVM image opts into the legacy libc ``nanosleep`` ABI,
which is independently qualified in the real guest before browser acceptance.

This is a compatibility shim, not a trust-boundary change.  It does not convert
runtime failures into success: unsupported configuration and libc wait failures
raise immediately.
"""
from __future__ import annotations

import ctypes
import errno
import math
import os
import time

BACKEND_ENV = "RESIDUAL_WEBVM_SLEEP_BACKEND"
LEGACY_NANOSLEEP = "legacy-nanosleep"


class _Timespec32(ctypes.Structure):
    _fields_ = [("tv_sec", ctypes.c_long), ("tv_nsec", ctypes.c_long)]


def _timespec(seconds: float) -> _Timespec32:
    if isinstance(seconds, bool) or not isinstance(seconds, (int, float)):
        raise TypeError("sleep duration must be a real number")
    value = float(seconds)
    if not math.isfinite(value):
        raise ValueError("sleep duration must be finite")
    if value < 0:
        raise ValueError("sleep duration must be non-negative")
    sec = int(value)
    nsec = int(round((value - sec) * 1_000_000_000))
    if nsec >= 1_000_000_000:
        sec += 1
        nsec -= 1_000_000_000
    if sec > 2_147_483_647:
        raise OverflowError("legacy nanosleep duration exceeds 32-bit timespec")
    return _Timespec32(sec, nsec)


def _legacy_nanosleep(seconds: float) -> None:
    if ctypes.sizeof(ctypes.c_long) != 4:
        raise RuntimeError("legacy-nanosleep backend requires a 32-bit long ABI")
    req = _timespec(seconds)
    rem = _Timespec32()
    libc = ctypes.CDLL(None, use_errno=True)
    nanosleep = libc.nanosleep
    nanosleep.argtypes = [ctypes.POINTER(_Timespec32), ctypes.POINTER(_Timespec32)]
    nanosleep.restype = ctypes.c_int
    while True:
        ctypes.set_errno(0)
        if int(nanosleep(ctypes.byref(req), ctypes.byref(rem))) == 0:
            return
        error = ctypes.get_errno()
        if error != errno.EINTR:
            raise OSError(error, os.strerror(error))
        req = _Timespec32(rem.tv_sec, rem.tv_nsec)


def sleep(seconds: float) -> None:
    """Sleep using the explicitly selected workbench backend."""
    backend = os.environ.get(BACKEND_ENV)
    if backend is None or backend == "":
        time.sleep(seconds)
        return
    if backend != LEGACY_NANOSLEEP:
        raise RuntimeError(f"unsupported WebVM sleep backend: {backend}")
    _legacy_nanosleep(seconds)
