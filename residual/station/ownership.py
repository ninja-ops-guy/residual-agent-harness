"""Single-process ownership and bounded Station lifetime admission.

Scope: trusted, stable local data directories; no distributed-filesystem, hostile
same-user filesystem mutation, arbitrary Store-user, or HA fencing claim.
"""
from __future__ import annotations

from contextlib import contextmanager
from functools import wraps
import hashlib
import math
import os
from pathlib import Path
import stat
import threading
import time

from residual.core import ContractError


class StationOwnershipError(ContractError):
    pass


class StationDataDirOwnership:
    _guard = threading.RLock()
    _owned = {}  # (creating PID, canonical path) -> unique acquisition token

    def __init__(self, root):
        self._pid = os.getpid()
        self._fd = None
        self._handle = None
        self._closed = False
        self._token = object()
        self._registered = False
        self.root = Path(root).expanduser().resolve(strict=False)
        self.key = (self._pid, os.path.normcase(str(self.root)))
        with self._guard:
            if self.key in self._owned:
                raise StationOwnershipError("Station data directory is already owned")
            self._owned[self.key] = self._token
            self._registered = True
        try:
            self._acquire_os_lock()
        except BaseException:
            self.close()
            raise

    def _acquire_os_lock(self):
        if os.name == "posix":
            import fcntl
            if not all(hasattr(os, flag) for flag in ("O_NOFOLLOW", "O_CLOEXEC", "O_NONBLOCK")):
                raise StationOwnershipError("Secure Station ownership locking is unavailable")
            self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
            try:
                fd = os.open(self.root / ".residual-station-owner.lock",
                             os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK,
                             0o600)
                self._fd = fd
                info = os.fstat(fd)
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                    raise StationOwnershipError("Unsafe Station ownership lock")
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise StationOwnershipError("Station ownership lock unavailable or already owned") from exc
            # Persistent lock inode: never truncate, unlink or write through it.
            return
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            create = kernel.CreateMutexW
            create.argtypes = (wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR)
            create.restype = wintypes.HANDLE
            close = kernel.CloseHandle
            close.argtypes = (wintypes.HANDLE,)
            close.restype = wintypes.BOOL
            digest = hashlib.sha256(self.key[1].encode("utf-8")).hexdigest()
            # Global prevents two login sessions claiming the same directory.
            # Object existence, not thread mutex ownership, is the admission test.
            ctypes.set_last_error(0)
            handle = create(None, False, "Global\\RESIDUAL-Station-" + digest)
            if not handle:
                raise StationOwnershipError("Station ownership locking is unavailable")
            error = ctypes.get_last_error()
            if error == 183:
                close(handle)
                raise StationOwnershipError("Station data directory is already owned")
            if error:
                close(handle)
                raise StationOwnershipError("Station ownership locking returned an unexpected status")
            self._handle = (handle, close)
            return
        raise StationOwnershipError("Station ownership locking is unavailable")

    def assert_live(self):
        if self._closed or os.getpid() != self._pid:
            raise StationOwnershipError("Station ownership is closed or inherited across fork")

    def close(self):
        if self._closed:
            return
        self._closed = True
        # Closing a fork child's descriptor must NOT issue LOCK_UN on the shared
        # open-file description; closing alone preserves the parent's flock.
        if self._fd is not None:
            fd, self._fd = self._fd, None
            os.close(fd)
        if self._handle is not None:
            handle, close = self._handle
            self._handle = None
            close(handle)
        if os.getpid() == self._pid and self._registered:
            with self._guard:
                if self._owned.get(self.key) is self._token:
                    del self._owned[self.key]
            self._registered = False

    def __enter__(self):
        self.assert_live()
        return self

    def __exit__(self, *exc):
        self.close()

    def __del__(self):
        try:
            self.close()
        except BaseException:
            pass


def _reset_registry_after_fork():
    StationDataDirOwnership._guard = threading.RLock()
    StationDataDirOwnership._owned = {}


if hasattr(os, "register_at_fork"):
    os.register_at_fork(after_in_child=_reset_registry_after_fork)


class StationLifecycle:
    """Close rejects new work, waits a bounded interval, and never unlocks busy work."""
    def __init__(self, ownership):
        self.ownership = ownership
        self._condition = threading.Condition(threading.RLock())
        self._local = threading.local()
        self._count = 0
        self._state = "OPEN"

    @contextmanager
    def operation(self):
        self.ownership.assert_live()
        depth = getattr(self._local, "depth", 0)
        with self._condition:
            if depth == 0:
                if self._state != "OPEN":
                    raise StationOwnershipError("Station is closing or closed")
                self._count += 1
            self._local.depth = depth + 1
        try:
            yield
        finally:
            with self._condition:
                self._local.depth = depth
                if depth == 0:
                    self._count -= 1
                    self._condition.notify_all()

    def reserve(self):
        """Reserve before starting a background job or attaching a server."""
        self.ownership.assert_live()
        with self._condition:
            if self._state != "OPEN" and not getattr(self._local, "depth", 0):
                raise StationOwnershipError("Station is closing or closed")
            self._count += 1
        return _Reservation(self)

    def close(self, timeout=5.0):
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout < 0:
            raise ValueError("close timeout must be finite and nonnegative")
        if getattr(self._local, "depth", 0):
            raise StationOwnershipError("Cannot close Station from an admitted operation")
        if os.getpid() != self.ownership._pid:
            raise StationOwnershipError("Cannot close an inherited Station")
        deadline = time.monotonic() + timeout
        with self._condition:
            if self._state == "CLOSED":
                return
            self._state = "CLOSING"
            while self._count:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise StationOwnershipError("Station still has admitted work; ownership retained")
                self._condition.wait(remaining)
            self.ownership.close()
            self._state = "CLOSED"


class _Reservation:
    def __init__(self, lifecycle):
        self.lifecycle = lifecycle
        self._released = False
        self._entered = False

    def __enter__(self):
        life = self.lifecycle
        life.ownership.assert_live()
        with life._condition:
            if self._released or self._entered or getattr(life._local, "depth", 0):
                raise StationOwnershipError("Invalid Station work reservation")
            self._entered = True
            life._local.depth = 1
        return self

    def __exit__(self, *exc):
        self.lifecycle._local.depth = 0
        self.cancel()

    def cancel(self):
        with self.lifecycle._condition:
            if not self._released:
                self._released = True
                self.lifecycle._count -= 1
                self.lifecycle._condition.notify_all()


def station_operation(function):
    @wraps(function)
    def guarded(self, *args, **kwargs):
        with self._lifecycle.operation():
            return function(self, *args, **kwargs)
    return guarded
