"""Trusted bootstrap for the Linux brokered worker. Never import this to sandbox the host.

The worker receives its source only AFTER a kill-by-default seccomp filter is
loaded. Direct filesystem, process creation, network, tracing and exec syscalls
are unavailable. Project access is exclusively through the parent's broker.
"""
from __future__ import annotations

import ctypes
import json
import math
import os
import resource
import sys
import time

PROFILE = "linux-seccomp-broker-v1"
MAX_FRAME = 2 * 1024 * 1024


class _Comparison(ctypes.Structure):
    _fields_ = [("arg", ctypes.c_uint), ("op", ctypes.c_int),
                ("a", ctypes.c_uint64), ("b", ctypes.c_uint64)]


def _install(memory_mb: int, wall_s: float, parent_pid: int) -> None:
    if sys.platform != "linux":
        raise RuntimeError("Linux is required")
    lib = ctypes.CDLL("libseccomp.so.2", use_errno=True)
    libc = ctypes.CDLL(None, use_errno=True)
    libc.prctl.restype = ctypes.c_int
    lib.seccomp_init.argtypes = [ctypes.c_uint32]
    lib.seccomp_init.restype = ctypes.c_void_p
    lib.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    lib.seccomp_syscall_resolve_name.restype = ctypes.c_int
    lib.seccomp_rule_add_array.argtypes = [ctypes.c_void_p, ctypes.c_uint32,
                                          ctypes.c_int, ctypes.c_uint,
                                          ctypes.POINTER(_Comparison)]
    lib.seccomp_rule_add_array.restype = ctypes.c_int
    lib.seccomp_load.argtypes = [ctypes.c_void_p]
    lib.seccomp_load.restype = ctypes.c_int
    lib.seccomp_release.argtypes = [ctypes.c_void_p]
    lib.seccomp_release.restype = None

    # No ambient credentials, descriptors, core dumps or privilege recovery.
    maximum = resource.getrlimit(resource.RLIMIT_NOFILE)[0]
    os.closerange(3, min(maximum, 1048576))
    if os.geteuid() == 0:
        os.setgroups([])
        os.setgid(65534)
        os.setuid(65534)
    for operation, argument in ((1, 9), (4, 0), (38, 1)):
        if libc.prctl(operation, argument, 0, 0, 0) != 0:
            raise RuntimeError("prctl unavailable")
    if os.getppid() != parent_pid:
        os._exit(120)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_NOFILE, (3, 3))
    resource.setrlimit(resource.RLIMIT_NPROC, (0, 0))
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
    ceiling = memory_mb * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (ceiling, ceiling))
    cpu = max(1, math.ceil(wall_s))
    resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu + 1))

    context = lib.seccomp_init(0x80000000)  # SCMP_ACT_KILL_PROCESS
    if not context:
        raise RuntimeError("seccomp initialization failed")
    try:
        def allow(name: str, comparisons: tuple = ()) -> None:
            number = lib.seccomp_syscall_resolve_name(name.encode("ascii"))
            if number < 0:
                return  # syscall absent on this architecture remains denied
            array = (_Comparison * len(comparisons))(*comparisons)
            if lib.seccomp_rule_add_array(context, 0x7fff0000, number,
                                          len(comparisons), array) != 0:
                raise RuntimeError("seccomp rule failed")

        # Anonymous memory and CPython housekeeping only; no descriptor creation.
        for name in ("brk", "munmap", "mremap", "madvise", "futex", "futex_time64",
                     "rt_sigaction", "rt_sigprocmask", "rt_sigreturn", "sigaltstack",
                     "clock_gettime", "clock_gettime64", "gettimeofday", "time",
                     "clock_nanosleep", "clock_nanosleep_time64", "nanosleep",
                     "getpid", "gettid", "getrandom", "sched_yield", "exit", "exit_group"):
            allow(name)
        # SCMP_CMP_MASKED_EQ: anonymous mappings only, never executable mappings.
        allow("mmap", (_Comparison(3, 7, 0x20, 0x20), _Comparison(2, 7, 4, 0)))
        allow("mmap2", (_Comparison(3, 7, 0x20, 0x20), _Comparison(2, 7, 4, 0)))
        allow("mprotect", (_Comparison(2, 7, 4, 0),))
        allow("read", (_Comparison(0, 4, 0, 0),))
        for descriptor in (1, 2):
            allow("write", (_Comparison(0, 4, descriptor, 0),))
        for descriptor in (0, 1, 2):
            allow("close", (_Comparison(0, 4, descriptor, 0),))
        if lib.seccomp_load(context) != 0:
            raise RuntimeError("kernel refused seccomp")
    finally:
        lib.seccomp_release(context)


def _send(value: dict) -> None:
    data = json.dumps(value, separators=(",", ":"), allow_nan=False).encode() + b"\n"
    if len(data) > MAX_FRAME:
        raise ValueError("frame too large")
    sys.stdout.buffer.write(data)
    sys.stdout.buffer.flush()


def _receive() -> dict:
    line = sys.stdin.buffer.readline(MAX_FRAME + 1)
    if not line.endswith(b"\n") or len(line) > MAX_FRAME:
        raise ValueError("invalid frame")
    value = json.loads(line)
    if not isinstance(value, dict):
        raise ValueError("invalid frame")
    return value


def main() -> int:
    try:
        _install(int(sys.argv[1]), float(sys.argv[2]), int(sys.argv[3]))
        _send({"event": "SandboxReady", "profile": PROFILE})
        envelope = _receive()
        if set(envelope) != {"source"} or not isinstance(envelope["source"], str):
            return 121
        sequence = 0

        def rpc(operation: str, **arguments):
            nonlocal sequence
            sequence += 1
            _send({"sequence": sequence, "operation": operation, "arguments": arguments})
            reply = _receive()
            if reply.get("sequence") != sequence or reply.get("ok") is not True:
                raise RuntimeError("broker refused operation")
            return reply.get("result")

        namespace = {
            "__name__": "__worker__",
            "read_file": lambda path: rpc("read_file", path=path),
            "write_file": lambda path, content: rpc("write_file", path=path, content=content),
            "delete_file": lambda path: rpc("delete_file", path=path),
        }
        exec(compile(envelope["source"], "<residual-worker>", "exec"), namespace, namespace)
        rpc("__complete__")
        return 0
    except BaseException:
        # Never format worker-controlled exceptions or open source for tracebacks.
        return 122


if __name__ == "__main__":
    os._exit(main())
