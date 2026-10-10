"""Fallback sandbox backend: rlimits + optional namespace launcher.

Requirement IDs (track B):
  B-R10: Resource limits MUST be enforced even in the weakest backend:
         RLIMIT_CPU (cpu_seconds), RLIMIT_AS (memory_mb), RLIMIT_NPROC
         (max_pids), plus a wall-clock timeout enforced with SIGKILL on the
         whole process group.
  B-R11: When user namespaces are available the subprocess backend MUST
         escalate to kernel isolation (mount namespace chroot for the fs
         allowlist, network namespace for DENY) via the _nslaunch helper and
         MUST then report Enforcement.KERNEL.
  B-R12: When neither bwrap nor user namespaces exist, the backend MUST
         report Enforcement.BEST_EFFORT and MUST still enforce rlimits,
         timeout, and output capture caps. Honest limitation: filesystem
         and network policy are then validated but not kernel-enforced.
  B-R13: Captured stdout/stderr MUST be capped at limits.max_output_bytes;
         excess MUST be discarded and the result flagged ``truncated``.
"""
from __future__ import annotations

import json
import os
import resource
import signal
import shutil
import subprocess
import sys
import tempfile
import time

from ..core import ContractError
from .backend import Enforcement
from .spec import NetworkPolicy, SandboxResult, SandboxSpec, Violation

def current_uid_processes() -> int:
    """Number of tasks (processes plus their threads) owned by our real UID.

    RLIMIT_NPROC charges every task of the real UID across the whole host —
    kernel thread accounting, not just process leaders — so the base MUST
    sum each owned process's thread count. Counting process leaders alone
    under-budgets on any thread-heavy host (CI agents, browsers, service
    workers) and makes every sandboxed fork fail with EAGAIN even though
    the sandbox itself is nearly idle (B-R10). The sandbox adds
    ``max_pids`` on top of this measured charge."""
    uid = os.getuid()
    count = 0
    for entry in os.listdir("/proc"):
        if not entry.isdigit():
            continue
        try:
            with open(f"/proc/{entry}/status", "rb") as fh:
                head = fh.read(1024)
            if f"Uid:\t{uid}\t".encode() not in head:
                continue
            for line in head.split(b"\n"):
                if line.startswith(b"Threads:"):
                    count += int(line.split()[1])
                    break
            else:
                count += 1
        except (OSError, ValueError):
            continue
    return count


def _apply_rlimits(spec: SandboxSpec, *, nproc_budget: int) -> None:
    """Runs in the child pre-exec (B-R10)."""
    lim = spec.limits
    resource.setrlimit(resource.RLIMIT_CPU, (lim.cpu_seconds, lim.cpu_seconds + 5))
    mem_bytes = lim.memory_mb << 20
    resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
    if nproc_budget:
        resource.setrlimit(resource.RLIMIT_NPROC, (nproc_budget, nproc_budget))
    resource.setrlimit(resource.RLIMIT_NOFILE, (256, 256))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def _classify(returncode: int, timed_out: bool) -> tuple[int | None, int | None, Violation]:
    if returncode < 0:
        sig = -returncode
        if timed_out:
            return None, sig, Violation.TIMEOUT
        if sig == signal.SIGXCPU:
            return None, sig, Violation.CPU_LIMIT
        return None, sig, Violation.SIGNALLED
    if returncode != 0:
        return returncode, None, Violation.EXIT_NONZERO
    return returncode, None, Violation.NONE


def run_contained(argv: list[str], spec: SandboxSpec, *, stdin: str = "",
                  enforcement: Enforcement = Enforcement.BEST_EFFORT) -> SandboxResult:
    """Run argv under rlimits + timeout; every failure is data (B-R4, B-R10)."""
    env = {"PATH": "/usr/bin:/bin", "HOME": "/tmp", **dict(spec.env)}
    if spec.network is NetworkPolicy.PROXY:
        proxy = f"http://{spec.proxy_host}:{spec.proxy_port}"
        env.update(http_proxy=proxy, https_proxy=proxy, HTTP_PROXY=proxy, HTTPS_PROXY=proxy)
        env["SANDBOX_PROXY_ALLOWLIST"] = ",".join(spec.proxy_allowlist)
    started = time.monotonic()
    timed_out = False
    proc = subprocess.Popen(
        argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        start_new_session=True, env=env, cwd=spec.workdir if os.path.isdir(spec.workdir) else "/",
        preexec_fn=lambda: _apply_rlimits(
            spec, nproc_budget=current_uid_processes() + spec.limits.max_pids), text=False)
    try:
        out, err = proc.communicate(stdin.encode(), timeout=spec.limits.timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
        out, err = proc.communicate()
    duration = time.monotonic() - started
    cap = spec.limits.max_output_bytes
    truncated = len(out) > cap or len(err) > cap
    exit_code, sig, violation = _classify(proc.returncode, timed_out)
    return SandboxResult(
        exit_code=exit_code, signal=sig, timed_out=timed_out, violation=violation,
        stdout=out[:cap].decode("utf-8", "replace"),
        stderr=err[:cap].decode("utf-8", "replace"),
        duration_seconds=duration, truncated=truncated,
        enforcement=enforcement.name.lower())


class SubprocessBackend:
    """rlimit-based backend; escalates to kernel namespaces when possible."""

    name = "subprocess"

    def __init__(self):
        self._spec: SandboxSpec | None = None
        self.enforcement = (Enforcement.KERNEL if self._launcher_usable()
                            else Enforcement.BEST_EFFORT)

    _launcher_cache: "bool | None" = None

    @classmethod
    def _launcher_usable(cls) -> bool:
        if cls._launcher_cache is not None:
            return cls._launcher_cache
        cls._launcher_cache = cls._probe_launcher()
        return cls._launcher_cache

    @staticmethod
    def _probe_launcher() -> bool:
        if not shutil.which("mount"):
            return False
        probe = os.path.join(tempfile.gettempdir(), f".nsprobe-{os.getpid()}")
        try:
            probe_fd, probe = tempfile.mkstemp(prefix=".nsprobe-")
            os.close(probe_fd)
            env = {"SANDBOX_LAUNCH_CONFIG": json.dumps(
                {"deny_net": True, "read": [], "write": [], "runtime": False})}
            r = subprocess.run([sys.executable, "-m", "residual.sandbox._nslaunch", "--probe"],
                               env=env, capture_output=True, timeout=15)
            return r.returncode == 0
        except Exception:
            return False
        finally:
            try:
                os.unlink(probe)
            except OSError:
                pass

    def start(self, spec: SandboxSpec) -> None:
        if spec.network is NetworkPolicy.ALLOW:
            raise ContractError("network ALLOW must be requested via an explicit opt-in wrapper")
        self._spec = spec

    def exec(self, argv: list[str], *, stdin: str = "") -> SandboxResult:
        if self._spec is None:
            raise RuntimeError("sandbox not started")
        spec = self._spec
        if not argv:
            raise ContractError("empty argv")
        if self.enforcement is Enforcement.KERNEL:
            config = {
                "deny_net": spec.network is NetworkPolicy.DENY,
                "read": list(spec.fs.read), "write": list(spec.fs.write),
                "workdir": spec.workdir, "runtime": True,
                "max_pids": spec.limits.max_pids, "memory_mb": spec.limits.memory_mb,
                "nproc_base": current_uid_processes(),
            }
            env = os.environ.copy()
            env["SANDBOX_LAUNCH_CONFIG"] = json.dumps(config)
            import residual  # ensure the launcher module is importable by path
            env["PYTHONPATH"] = os.path.dirname(os.path.dirname(os.path.abspath(residual.__file__)))
            # rlimits apply inside the launcher; it exec's the payload.
            wrapped = [sys.executable, "-m", "residual.sandbox._nslaunch", "--"] + argv
            return run_contained_env(wrapped, spec, stdin=stdin, extra_env=env,
                                     enforcement=Enforcement.KERNEL)
        return run_contained(argv, spec, stdin=stdin,
                             enforcement=Enforcement.BEST_EFFORT)

    def stop(self) -> None:
        self._spec = None


def run_contained_env(argv: list[str], spec: SandboxSpec, *, stdin: str,
                      extra_env: dict,
                      enforcement: Enforcement = Enforcement.BEST_EFFORT) -> SandboxResult:
    """Like run_contained but preserves a caller-supplied environment."""
    started = time.monotonic()
    timed_out = False
    env = {**extra_env, **dict(spec.env)}
    proc = subprocess.Popen(
        argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        start_new_session=True, env=env, cwd="/",
        preexec_fn=lambda: _apply_rlimits(spec, nproc_budget=0), text=False)
    try:
        out, err = proc.communicate(stdin.encode(), timeout=spec.limits.timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
        out, err = proc.communicate()
    duration = time.monotonic() - started
    cap = spec.limits.max_output_bytes
    truncated = len(out) > cap or len(err) > cap
    exit_code, sig, violation = _classify(proc.returncode, timed_out)
    return SandboxResult(
        exit_code=exit_code, signal=sig, timed_out=timed_out, violation=violation,
        stdout=out[:cap].decode("utf-8", "replace"),
        stderr=err[:cap].decode("utf-8", "replace"),
        duration_seconds=duration, truncated=truncated,
        enforcement=enforcement.name.lower())
