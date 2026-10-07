"""OS-isolated M4 project verification runner (Linux user/mount/PID/net namespaces).

This module provides the *only* execution boundary under which untrusted,
candidate-dependent project verification commands may run. Isolation is provided
by the kernel, not by environment hygiene:

* a private mount namespace with a minimal read-only root (toolchain binds,
  tmpfs ``/tmp`` scratch, the candidate worktree bind-mounted read-only at its
  original absolute path) followed by ``chroot`` — host ``$HOME``, credentials,
  ``/etc`` and the source repository are unreachable;
* a private network namespace with no configured interfaces (network deny by
  construction, not by policy);
* a private PID namespace — descendant processes are contained and die with the
  namespace init, so fork/daemon escapes cannot survive;
* private IPC and UTS namespaces — SysV IPC/POSIX mqueue objects created by the
  candidate are invisible to the host (no shared ``ipcs`` namespace), and the
  hostname is isolated;
* ``RLIMIT_AS`` memory, ``RLIMIT_CPU`` CPU and a finite parent-side wall-clock
  deadline; bounded stdout/stderr capture with hashing;
* deterministic typed outcomes: PASS / FAIL / TIMEOUT / UNKNOWN / ERROR
  (TIMEOUT = parent-side wall-clock kill, deterministic returncode 124).

If any prerequisite is missing (non-Linux platform, no ``unshare`` binary, or a
failed capability probe) the runner FAILS CLOSED: :func:`run_isolated` returns
UNKNOWN/ERROR and :func:`require_isolation` raises. There is deliberately no
fallback to unsandboxed execution.
"""
from __future__ import annotations

import hashlib
import math
import os
from dataclasses import dataclass
from pathlib import Path
import selectors
import shutil
import signal
import subprocess
import sys
import tempfile
import time

from .m4_protocol import SANDBOX_ERROR_EXIT, SANDBOX_ERROR_PREFIX, SANDBOX_TIMEOUT_EXIT
from .worker_contract import WorkerContractError


class M4SandboxError(WorkerContractError):
    """Isolation was required but unavailable, or the sandbox itself failed."""


SANDBOX_PROFILE = "linux-userns-isolated-v1"
_CHILD = str(Path(__file__).with_name("_isolated_child.py"))

MIN_TIMEOUT_S = 1.0
MAX_TIMEOUT_S = 900.0
MIN_OUTPUT_LIMIT = 1
MAX_OUTPUT_LIMIT = 16 * 1024 * 1024
MIN_MEMORY_MB = 32
MAX_MEMORY_MB = 4096

_probe_cache: "tuple[bool, str] | None" = None


def _unshare_argv(command: list[str]) -> list[str] | None:
    binary = shutil.which("unshare", path="/usr/bin:/bin")
    if binary is None:
        return None
    return [
        binary, "--user", "--map-root-user", "--mount", "--pid", "--fork",
        "--net", "--ipc", "--uts", "--kill-child", "--", *command,
    ]


def probe_isolation() -> tuple[bool, str]:
    """Probe once whether kernel namespaces for the sandbox are usable."""
    global _probe_cache
    if _probe_cache is not None:
        return _probe_cache
    if sys.platform != "linux" or os.name != "posix":
        _probe_cache = (False, "platform_not_linux")
        return _probe_cache
    if not hasattr(os, "chroot"):
        _probe_cache = (False, "chroot_unavailable")
        return _probe_cache
    argv = _unshare_argv(["/usr/bin/env", "-i", "sh", "-c", "true"])
    if argv is None:
        _probe_cache = (False, "unshare_binary_missing")
        return _probe_cache
    try:
        result = subprocess.run(
            argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE, timeout=20, check=False,
            env={"PATH": "/usr/bin:/bin"},
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        _probe_cache = (False, f"probe_launch_failed:{type(exc).__name__}")
        return _probe_cache
    if result.returncode != 0:
        _probe_cache = (False, "namespace_probe_failed")
        return _probe_cache
    _probe_cache = (True, "ok")
    return _probe_cache


def require_isolation() -> None:
    ok, reason = probe_isolation()
    if not ok:
        raise M4SandboxError(
            f"isolated project verification is unavailable ({reason}); "
            "untrusted candidate execution is blocked, no unsandboxed fallback exists"
        )


@dataclass(frozen=True)
class IsolatedResult:
    status: str  # "pass" | "fail" | "timeout" | "unknown" | "error"
    returncode: int | None
    stdout_sha256: str
    stderr_sha256: str
    reason: str  # exit | timeout | output_limit | sandbox_error | launch_failed | isolation_unavailable
    execution_boundary: str = SANDBOX_PROFILE
    timed_out: bool = False  # parent-side wall-clock timeout (returncode 124)


def _invalid(request: str) -> M4SandboxError:
    return M4SandboxError(f"invalid isolation request: {request}")


def run_isolated(argv: tuple[str, ...], worktree: Path, *, timeout_s: float,
                 output_limit: int, memory_mb: int = 512,
                 cpu_s: float | None = None) -> IsolatedResult:
    """Run ``argv`` against ``worktree`` inside the isolation boundary.

    Never raises for *candidate* behaviour (crashes, timeouts, runaway output
    are FAIL); raises/returns ERROR only for sandbox infrastructure failure.
    """
    if not isinstance(argv, tuple) or not argv or not all(
            isinstance(a, str) and a and "\x00" not in a for a in argv):
        raise _invalid("argv")
    if type(timeout_s) not in (int, float) or not math.isfinite(timeout_s) \
            or not MIN_TIMEOUT_S <= timeout_s <= MAX_TIMEOUT_S:
        raise _invalid("timeout_s")
    if type(output_limit) is not int or not MIN_OUTPUT_LIMIT <= output_limit <= MAX_OUTPUT_LIMIT:
        raise _invalid("output_limit")
    if type(memory_mb) is not int or not MIN_MEMORY_MB <= memory_mb <= MAX_MEMORY_MB:
        raise _invalid("memory_mb")
    cpu = int(math.ceil(min(timeout_s, cpu_s if cpu_s is not None else timeout_s)))
    empty = hashlib.sha256(b"").hexdigest()

    ok, reason = probe_isolation()
    if not ok:
        return IsolatedResult("unknown", None, empty, empty,
                              f"isolation_unavailable:{reason}")

    worktree = Path(worktree)
    scratch = tempfile.mkdtemp(prefix="m4-sandbox-root-")
    spec = {
        "argv": list(argv),
        "worktree": str(worktree),
        "newroot": scratch,
        "memory_mb": memory_mb,
        "cpu_s": cpu,
    }
    import json

    command = _unshare_argv([sys.executable, _CHILD])
    if command is None:  # pragma: no cover - probe already covers this
        return IsolatedResult("unknown", None, empty, empty, "isolation_unavailable:unshare_binary_missing")

    ready_r, ready_w = os.pipe()
    hashes = [hashlib.sha256(), hashlib.sha256()]
    process: subprocess.Popen | None = None
    try:
        try:
            process = subprocess.Popen(
                command,
                cwd=str(worktree),
                env={"PATH": "/usr/bin:/bin", "M4_SANDBOX_READY_FD": str(ready_w)},
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
                close_fds=True,
                pass_fds=(ready_w,),
            )
        except OSError:
            return IsolatedResult("error", None, empty, empty, "launch_failed")
        os.close(ready_w)
        ready_w = -1
        process.stdin.write(json.dumps(spec).encode("utf-8"))
        process.stdin.close()

        # Wait for the readiness byte: EOF means the namespace/chroot/limit
        # setup failed before exec (a sandbox ERROR, never a candidate FAIL).
        os.set_blocking(ready_r, False)
        deadline = time.monotonic() + timeout_s
        ready = b""
        while time.monotonic() < deadline:
            try:
                chunk = os.read(ready_r, 1)
            except BlockingIOError:
                chunk = None
            if chunk == b"":
                break  # EOF: child exited before exec (setup failure)
            if chunk:
                ready = chunk
                break
            time.sleep(0.01)
        os.close(ready_r)
        ready_r = -1
        if ready != b"1":
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=5)
            return IsolatedResult("error", process.returncode, empty, empty,
                                  "sandbox_error")

        reason_out = "exit"
        captured = 0
        prefix_probe = SANDBOX_ERROR_PREFIX.encode("ascii")
        stderr_head = bytearray()
        try:
            with selectors.DefaultSelector() as selector:
                for index, stream in enumerate((process.stdout, process.stderr)):
                    os.set_blocking(stream.fileno(), False)
                    selector.register(stream, selectors.EVENT_READ, index)
                while selector.get_map() or process.poll() is None:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        reason_out = "timeout"
                        break
                    for key, _ in selector.select(min(remaining, 0.05)):
                        chunk = os.read(key.fileobj.fileno(), 65536)
                        if not chunk:
                            selector.unregister(key.fileobj)
                            continue
                        permitted = max(0, output_limit - captured)
                        hashes[key.data].update(chunk[:permitted])
                        captured += len(chunk)
                        if key.data == 1 and len(stderr_head) < len(prefix_probe):
                            stderr_head += chunk[:len(prefix_probe) - len(stderr_head)]
                        if captured > output_limit:
                            reason_out = "output_limit"
                            break
                    if reason_out != "exit":
                        break
        finally:
            # Killing the leader (PID-1 of the private namespace) makes the
            # kernel kill every descendant; killpg covers the unsandboxed
            # window before the namespace existed.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=10)

        if reason_out == "timeout":
            # Typed parent-side wall-clock timeout: deterministic returncode
            # (SANDBOX_TIMEOUT_EXIT), never retyped as candidate FAIL/ERROR.
            return IsolatedResult("timeout", SANDBOX_TIMEOUT_EXIT,
                                  hashes[0].hexdigest(), hashes[1].hexdigest(),
                                  reason_out, timed_out=True)
        if reason_out == "exit" and process.returncode == 0:
            status = "pass"
        elif reason_out == "exit" and process.returncode == SANDBOX_ERROR_EXIT:
            if bytes(stderr_head).startswith(prefix_probe):
                # The child exec() failed after the sandbox was ready (e.g.
                # missing executable): the candidate never launched, which the
                # fixture lane types as unknown/launch_failed — not a
                # candidate FAIL and not a sandbox infrastructure ERROR.
                status = "unknown"
                reason_out = "launch_failed"
            else:
                # A candidate process itself exiting with code 125 is
                # ordinary candidate behaviour: FAIL with exit code 125.
                status = "fail"
        else:
            status = "fail"
        return IsolatedResult(status, process.returncode,
                              hashes[0].hexdigest(), hashes[1].hexdigest(), reason_out)
    finally:
        if ready_w >= 0:
            os.close(ready_w)
        if ready_r >= 0:
            os.close(ready_r)
        if process is not None and process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=10)
        shutil_rmtree(scratch)


def shutil_rmtree(path: str) -> None:
    import shutil
    shutil.rmtree(path, ignore_errors=True)
