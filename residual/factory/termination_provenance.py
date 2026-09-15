"""Single-owner Linux process termination provenance for Factory execution.

This module deliberately separates an observed process signal from the claimed
cause of termination. Host-requested termination is recorded before signaling;
waitid(..., WNOWAIT) is used only for non-consuming observation where available;
one ProcessControl.reap() path performs the consuming wait.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import os
from pathlib import Path
import select
import signal
import subprocess
import threading
import time
from typing import Any, Callable


def _proc_start_ticks(pid: int) -> int | None:
    try:
        text = Path(f"/proc/{pid}/stat").read_text()
        remainder = text.rsplit(")", 1)[1].split()
        return int(remainder[19])  # field 22, with field 3 at remainder[0]
    except (OSError, ValueError, IndexError):
        return None


def _boot_id() -> str | None:
    try:
        value = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
        return value or None
    except OSError:
        return None


def _cgroup_memory_events() -> dict[str, int] | None:
    """Best-effort cgroup-v2 memory.events snapshot; never infer ownership from it."""
    try:
        cgroup_path = None
        for line in Path("/proc/self/cgroup").read_text().splitlines():
            if line.startswith("0::"):
                cgroup_path = line[3:]
                break
        if cgroup_path is None:
            return None
        path = Path("/sys/fs/cgroup") / cgroup_path.lstrip("/") / "memory.events"
        values: dict[str, int] = {}
        for line in path.read_text().splitlines():
            key, value = line.split(None, 1)
            values[key] = int(value)
        return values
    except (OSError, ValueError):
        return None


@dataclass(frozen=True)
class ProcessIdentity:
    correlation_id: str
    pid: int
    pid_start_time_ticks: int | None
    boot_id: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TerminationRecord:
    correlation_id: str
    pid: int
    pid_start_time_ticks: int | None
    boot_id: str | None
    requested_by: str | None
    request_boundary: str | None
    request_field: str | None
    request_action: dict[str, Any] | None
    requested_monotonic_ns: int | None
    observed_monotonic_ns: int | None
    reaped_monotonic_ns: int | None
    returncode: int | None
    observed_signal: int | None
    waitid_code: int | None
    waitid_status: int | None
    cgroup_memory_events_before: dict[str, int] | None
    cgroup_memory_events_after: dict[str, int] | None
    cgroup_oom_kill_delta: int | None
    classification: str
    kernel_audit_evidence: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ProcessControl:
    """Own pid identity, host termination intent, observation, and the single reap."""

    def __init__(self, process: subprocess.Popen, *, correlation_id: str,
                 clock_ns: Callable[[], int] = time.monotonic_ns):
        if not hasattr(os, "pidfd_open") or not hasattr(signal, "pidfd_send_signal"):
            raise RuntimeError("pidfd-based process ownership is required")
        self.process = process
        self.pidfd = os.pidfd_open(process.pid, 0)
        self.identity = ProcessIdentity(
            correlation_id=correlation_id,
            pid=process.pid,
            pid_start_time_ticks=_proc_start_ticks(process.pid),
            boot_id=_boot_id(),
        )
        self._clock_ns = clock_ns
        self._state_lock = threading.RLock()
        self._reap_lock = threading.Lock()
        self.reason: tuple[str, str, dict[str, Any]] | None = None
        self.requested_by: str | None = None
        self.requested_monotonic_ns: int | None = None
        self.termination_requested = threading.Event()
        self.stopped = threading.Event()
        self._waitid_code: int | None = None
        self._waitid_status: int | None = None
        self._observed_monotonic_ns: int | None = None
        self._reaped_monotonic_ns: int | None = None
        self._memory_before = _cgroup_memory_events()
        self._memory_after: dict[str, int] | None = None
        self._reaped = False

    @property
    def reaped(self) -> bool:
        with self._state_lock:
            return self._reaped

    def exited(self) -> bool:
        with self._state_lock:
            if self._reaped:
                return True
            pidfd = self.pidfd
        if pidfd < 0:
            return True
        try:
            return bool(select.select([pidfd], [], [], 0)[0])
        except (OSError, ValueError):
            return False

    def _observe_exit_wnowait(self) -> None:
        with self._state_lock:
            if self._observed_monotonic_ns is not None:
                return
        if not hasattr(os, "waitid") or not hasattr(os, "WNOWAIT"):
            return
        flags = os.WEXITED | os.WNOHANG | os.WNOWAIT
        idtype = getattr(os, "P_PIDFD", None)
        idvalue = self.pidfd
        if idtype is None:
            idtype, idvalue = os.P_PID, self.process.pid
        try:
            info = os.waitid(idtype, idvalue, flags)
        except (ChildProcessError, OSError):
            return
        if info is None:
            return
        with self._state_lock:
            self._waitid_code = int(info.si_code)
            self._waitid_status = int(info.si_status)
            self._observed_monotonic_ns = self._clock_ns()

    def reap(self, timeout: float = 2.0) -> int:
        """The only consuming wait path for a ProcessControl-owned child."""
        with self._reap_lock:
            with self._state_lock:
                if self._reaped:
                    assert self.process.returncode is not None
                    return self.process.returncode
                pidfd = self.pidfd
            ready = select.select([pidfd], [], [], timeout)[0]
            if not ready:
                raise subprocess.TimeoutExpired(self.process.args, timeout)
            self._observe_exit_wnowait()
            returncode = self.process.wait(timeout=timeout)
            with self._state_lock:
                if self._observed_monotonic_ns is None:
                    self._observed_monotonic_ns = self._clock_ns()
                self._reaped_monotonic_ns = self._clock_ns()
                self._memory_after = _cgroup_memory_events()
                self._reaped = True
                self.stopped.set()
            return returncode

    def kill(self, reason: tuple[str, str, dict[str, Any]] | None = None, *,
             requester: str = "runtime") -> None:
        """Record host intent before SIGKILL, then route all consumption through reap()."""
        if self.exited():
            self.reap(timeout=2.0)
            return
        self.termination_requested.set()
        with self._state_lock:
            if reason is not None and self.reason is None:
                boundary, field, action = reason
                self.reason = (boundary, field, dict(action))
                self.requested_by = requester
                self.requested_monotonic_ns = self._clock_ns()
        try:
            signal.pidfd_send_signal(self.pidfd, signal.SIGKILL)
        except ProcessLookupError:
            pass
        self.reap(timeout=2.0)

    def _classification(self, observed_signal: int | None, oom_delta: int | None) -> str:
        with self._state_lock:
            requester = self.requested_by
            reason = self.reason
        if requester == "watchdog" and reason is not None:
            if reason[1] == "wall_clock_budget_s":
                return "watchdog_wall_clock"
            if reason[1] == "memory_limit_mb":
                return "watchdog_memory"
            if reason[1] == "lease_generation":
                return "watchdog_lease_fence"
            return "watchdog_requested"
        if requester == "operator":
            return "operator_cancel"
        if requester == "guard":
            return "guard_contract_violation"
        if requester == "runtime":
            return "runtime_cleanup"
        if observed_signal == signal.SIGSYS:
            return "kernel_sigsys"
        if observed_signal == signal.SIGKILL:
            return "unknown_sigkill_with_cgroup_oom_activity" if oom_delta and oom_delta > 0 else "unknown_sigkill"
        if observed_signal is not None:
            return "external_signal"
        if self.process.returncode == 0:
            return "clean_exit"
        return "process_exit_nonzero"

    def termination_record(self) -> TerminationRecord:
        if not self.reaped:
            raise RuntimeError("termination record requires a reaped process")
        with self._state_lock:
            reason = self.reason
            before = self._memory_before
            after = self._memory_after
            returncode = self.process.returncode
            observed_signal = -returncode if returncode is not None and returncode < 0 else None
            oom_delta = None
            if before is not None and after is not None:
                oom_delta = after.get("oom_kill", 0) - before.get("oom_kill", 0)
            boundary = reason[0] if reason is not None else None
            field = reason[1] if reason is not None else None
            action = dict(reason[2]) if reason is not None else None
            classification = self._classification(observed_signal, oom_delta)
            return TerminationRecord(
                correlation_id=self.identity.correlation_id,
                pid=self.identity.pid,
                pid_start_time_ticks=self.identity.pid_start_time_ticks,
                boot_id=self.identity.boot_id,
                requested_by=self.requested_by,
                request_boundary=boundary,
                request_field=field,
                request_action=action,
                requested_monotonic_ns=self.requested_monotonic_ns,
                observed_monotonic_ns=self._observed_monotonic_ns,
                reaped_monotonic_ns=self._reaped_monotonic_ns,
                returncode=returncode,
                observed_signal=observed_signal,
                waitid_code=self._waitid_code,
                waitid_status=self._waitid_status,
                cgroup_memory_events_before=before,
                cgroup_memory_events_after=after,
                cgroup_oom_kill_delta=oom_delta,
                classification=classification,
                kernel_audit_evidence="not_collected_by_unprivileged_runtime",
            )

    def close(self) -> None:
        with self._state_lock:
            if self.pidfd >= 0:
                os.close(self.pidfd)
                self.pidfd = -1
