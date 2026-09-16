"""Single-owner Linux process termination provenance for Factory execution.

This module deliberately separates an observed process signal from the claimed
cause of termination. Host-requested termination is recorded before signaling;
waitid(..., WNOWAIT) is used only for non-consuming observation where available;
one ProcessControl.reap() path performs the consuming wait.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import asdict, dataclass, fields
import errno
import os
from pathlib import Path
import select
import signal
import subprocess
import threading
import time
from types import MappingProxyType
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


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


@dataclass(frozen=True)
class TerminationRecord:
    correlation_id: str
    pid: int
    pid_start_time_ticks: int | None
    boot_id: str | None
    requested_by: str | None
    request_boundary: str | None
    request_field: str | None
    request_action: Mapping[str, Any] | None
    requested_monotonic_ns: int | None
    observed_monotonic_ns: int | None
    reaped_monotonic_ns: int | None
    returncode: int | None
    observed_signal: int | None
    waitid_code: int | None
    waitid_status: int | None
    cgroup_memory_events_before: Mapping[str, int] | None
    cgroup_memory_events_after: Mapping[str, int] | None
    cgroup_oom_kill_delta: int | None
    classification: str
    kernel_audit_evidence: str

    def __post_init__(self) -> None:
        for name in ("request_action", "cgroup_memory_events_before", "cgroup_memory_events_after"):
            object.__setattr__(self, name, _freeze(getattr(self, name)))

    def to_dict(self) -> dict[str, Any]:
        # asdict() cannot deepcopy mappingproxy; exports must be detached/mutable.
        return {field.name: _thaw(getattr(self, field.name)) for field in fields(self)}


class ProcessControl:
    """Own pid identity, termination intent, observation, and exactly one reap.

    The state lock covers every nonblocking pidfd probe and signal. close() is
    legal only after reap(), so it cannot invalidate a blocking reaper's fd.
    The reap lock never prevents another thread from signaling a live child.
    Callers must not poll/wait/communicate on the owned Popen independently.
    """

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
        self.reap_timed_out = threading.Event()
        self._signal_sent = False
        self._waitid_code: int | None = None
        self._waitid_status: int | None = None
        self._waitid_invalid = False
        self._observed_monotonic_ns: int | None = None
        self._reaped_monotonic_ns: int | None = None
        self._memory_before = _cgroup_memory_events()
        self._memory_after: dict[str, int] | None = None
        self._reaped = False
        self._record: TerminationRecord | None = None
        self._returncode: int | None = None

    @property
    def reaped(self) -> bool:
        with self._state_lock:
            return self._reaped

    def exited(self) -> bool:
        """Non-consuming observation; a broken descriptor is not exit evidence."""
        with self._state_lock:
            if self._reaped:
                return True
            if self.pidfd < 0:
                raise RuntimeError("unreaped process has no owned pidfd")
            # Keep ownership locked through the syscall, including fd reuse.
            return bool(select.select([self.pidfd], [], [], 0)[0])

    def _observe_exit_wnowait(self) -> None:
        with self._state_lock:
            # Called only under _reap_lock. close() cannot run before _reaped is set.
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
            except OSError as exc:
                # Unsupported observation permits fallback, but ECHILD/EBADF and
                # other unexpected errors are evidence gaps, not clean exits.
                self._waitid_invalid = exc.errno not in (errno.ENOSYS, errno.EINVAL, errno.ENOTSUP)
                return
            if info is None:
                return
            self._waitid_code = int(info.si_code)
            self._waitid_status = int(info.si_status)
            self._observed_monotonic_ns = self._clock_ns()

    def reap(self, timeout: float = 2.0) -> int:
        """The only consuming wait path; repeated/concurrent calls share one result."""
        with self._reap_lock:
            with self._state_lock:
                if self._reaped:
                    assert self._returncode is not None
                    return self._returncode
                pidfd = self.pidfd
                if pidfd < 0:
                    raise RuntimeError("cannot reap without the owned pidfd")
            # Do not hold _state_lock while waiting: a watchdog may need to kill.
            ready = select.select([pidfd], [], [], timeout)[0]
            if not ready:
                raise subprocess.TimeoutExpired(self.process.args, timeout)
            self._observe_exit_wnowait()
            returncode = self.process.wait(timeout=timeout)
            with self._state_lock:
                self._returncode = returncode
                if self._observed_monotonic_ns is None:
                    self._observed_monotonic_ns = self._clock_ns()
                self._reaped_monotonic_ns = self._clock_ns()
                self._memory_after = _cgroup_memory_events()
                self._record = self._build_record()
                self._reaped = True
                self.stopped.set()
            return returncode

    def kill(self, reason: tuple[str, str, dict[str, Any]] | None = None, *,
             requester: str = "runtime") -> None:
        """Request SIGKILL if still live, then synchronously reap.

        An already-observed exit is only reaped: a late caller is not its killer
        and cannot relabel the record. For a live child, the first host intent
        (even with reason=None) is recorded before signaling. Intent is not
        proof of causation: the child can exit independently before delivery.
        """
        with self._state_lock:
            if self._reaped:
                return
            if not self.exited():
                if self.requested_monotonic_ns is None:
                    self.reason = deepcopy(reason)
                    self.requested_by = requester
                    self.requested_monotonic_ns = self._clock_ns()
                # Publish only after the first reason/requester is available.
                self.termination_requested.set()
                if not self._signal_sent:
                    try:
                        signal.pidfd_send_signal(self.pidfd, signal.SIGKILL)
                        self._signal_sent = True
                    except ProcessLookupError:
                        pass  # exit won the race; do not invent a delivered kill
        # Reap OUTSIDE the state lock (reap() takes only _reap_lock): a stuck
        # reap must never serialize a concurrent killer. A reap timeout is a
        # typed condition, not an escaping exception: record reap_timed_out
        # and, when no primary reason exists, the distinct reap_timeout reason.
        # `stopped` is NOT set: it is evidence of an actually reaped process
        # (see reap()), and this child may still be live. Callers needing
        # completion must drive a follow-up reap/escalation; termination_record()
        # continues to refuse an unreaped process.
        try:
            self.reap(timeout=2.0)
        except subprocess.TimeoutExpired:
            self.reap_timed_out.set()
            with self._state_lock:
                if self.reason is None:
                    self.reason = ("resource", "reap_timeout", {"timeout_s": 2})
                    self.requested_by = requester
                    self.requested_monotonic_ns = self._clock_ns()

    def _exit_outcome(self) -> tuple[int | None, int | None, bool]:
        """Prefer typed waitid exit metadata and cross-check the consuming wait.

        Both are kernel wait results; neither identifies the signal sender.
        CLD_DUMPED is a signal death too. Inconsistent evidence stays UNKNOWN.
        """
        code, status = self._waitid_code, self._waitid_status
        value = self._returncode
        valid = type(value) is int
        if code is not None or status is not None:
            if code == getattr(os, "CLD_EXITED", 1) and type(status) is int and 0 <= status <= 255:
                value = status
            elif code in (getattr(os, "CLD_KILLED", 2), getattr(os, "CLD_DUMPED", 3)) and type(status) is int and 0 < status < signal.NSIG:
                value = -status
            else:
                valid = False
            valid = valid and value == self._returncode
        valid = valid and not self._waitid_invalid
        observed_signal = -value if type(value) is int and value < 0 else None
        exitcode = value if type(value) is int and value >= 0 else None
        return observed_signal, exitcode, valid

    def _classification(self, observed_signal: int | None, exitcode: int | None,
                        oom_delta: int | None, consistent: bool) -> str:
        if not consistent:
            return "unknown_wait_status"
        # Host requests here send SIGKILL only. They cannot explain SIGSYS,
        # another signal, or a normal exit, even if recorded just before exit.
        if observed_signal == signal.SIGSYS:
            return "kernel_sigsys"
        if observed_signal == signal.SIGKILL:
            requester, reason = self.requested_by, self.reason
            if self._signal_sent:
                if requester == "watchdog" and reason is not None:
                    return {"wall_clock_budget_s": "watchdog_wall_clock",
                            "memory_limit_mb": "watchdog_memory",
                            "lease_generation": "watchdog_lease_fence"}.get(reason[1], "watchdog_requested")
                if requester in ("operator", "guard", "runtime"):
                    return {"operator": "operator_cancel", "guard": "guard_contract_violation",
                            "runtime": "runtime_cleanup"}[requester]
            return "unknown_sigkill_with_cgroup_oom_activity" if oom_delta and oom_delta > 0 else "unknown_sigkill"
        if observed_signal is not None:
            return "external_signal"
        return "clean_exit" if exitcode == 0 else "process_exit_nonzero"

    def _build_record(self) -> TerminationRecord:
        reason = self.reason
        before, after = self._memory_before, self._memory_after
        observed_signal, exitcode, consistent = self._exit_outcome()
        oom_delta = None
        if before is not None and after is not None:
            oom_delta = after.get("oom_kill", 0) - before.get("oom_kill", 0)
        return TerminationRecord(
            correlation_id=self.identity.correlation_id,
            pid=self.identity.pid,
            pid_start_time_ticks=self.identity.pid_start_time_ticks,
            boot_id=self.identity.boot_id,
            requested_by=self.requested_by,
            request_boundary=reason[0] if reason is not None else None,
            request_field=reason[1] if reason is not None else None,
            request_action=reason[2] if reason is not None else None,
            requested_monotonic_ns=self.requested_monotonic_ns,
            observed_monotonic_ns=self._observed_monotonic_ns,
            reaped_monotonic_ns=self._reaped_monotonic_ns,
            returncode=self._returncode,
            observed_signal=observed_signal,
            waitid_code=self._waitid_code,
            waitid_status=self._waitid_status,
            cgroup_memory_events_before=before,
            cgroup_memory_events_after=after,
            cgroup_oom_kill_delta=oom_delta,
            classification=self._classification(observed_signal, exitcode, oom_delta, consistent),
            kernel_audit_evidence="not_collected_by_unprivileged_runtime",
        )

    def termination_record(self) -> TerminationRecord:
        with self._state_lock:
            if not self._reaped or self._record is None:
                raise RuntimeError("termination record requires a reaped process")
            return self._record

    def close(self) -> None:
        """Release the pidfd after reaping; idempotent, never an exit assertion."""
        with self._state_lock:
            if not self._reaped:
                raise RuntimeError("cannot close process control before reap")
            if self.pidfd >= 0:
                descriptor, self.pidfd = self.pidfd, -1
                os.close(descriptor)
