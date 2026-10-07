"""Containment tests (track B): fork bomb, memory cap, fs escape,
network deny, timeout kill, signal capture.

Tests that require kernel-level isolation are skipped with an explicit
reason when the environment only offers Enforcement.BEST_EFFORT; the
rlimit/timeout tests run in every backend.
"""
from __future__ import annotations

import sys

import pytest

from residual.sandbox import (Enforcement, FsAllowlist, SandboxLimits,
                              SandboxSpec, Violation, select_backend)

PY = sys.executable


@pytest.fixture(scope="module")
def backend():
    return select_backend()


@pytest.fixture()
def spec(tmp_path):
    return SandboxSpec(
        name="containment",
        fs=FsAllowlist(write=(str(tmp_path),)),
        limits=SandboxLimits(cpu_seconds=15, memory_mb=128, max_pids=25,
                             timeout_seconds=8))


def test_success_path(backend, spec):
    backend.start(spec)
    result = backend.exec(["/bin/echo", "sandbox-ok"])
    assert result.ok and result.stdout.strip() == "sandbox-ok"
    backend.stop()


def test_nonzero_exit_captured(backend, spec):
    backend.start(spec)
    result = backend.exec(["/bin/bash", "-c", "exit 7"])
    assert result.exit_code == 7 and result.violation is Violation.EXIT_NONZERO
    backend.stop()


def test_signal_captured(backend, spec):
    backend.start(spec)
    # Synchronous SIGSEGV (bad dereference) kills even a PID-1 payload.
    result = backend.exec([PY, "-c", "import ctypes; ctypes.string_at(0)"])
    assert not result.ok
    assert (result.signal == 11) or (result.exit_code in (-11, 139, 1))
    assert result.violation in (Violation.SIGNALLED, Violation.EXIT_NONZERO)
    backend.stop()


def test_timeout_kills(backend, spec):
    backend.start(spec)
    result = backend.exec(["/bin/sleep", "600"])
    assert result.timed_out and result.violation is Violation.TIMEOUT
    assert result.duration_seconds < 60  # actually killed, not abandoned
    backend.stop()


def test_memory_cap_enforced(backend, spec):
    backend.start(spec)
    code = "x=[]\nwhile True: x.append(b' ' * 10**6)"
    result = backend.exec([PY, "-c", code])
    assert not result.ok
    # Either Python hit RLIMIT_AS (MemoryError) or the kernel killed it;
    # it MUST NOT complete and MUST NOT take the host down.
    assert "MemoryError" in result.stderr or result.violation in (
        Violation.EXIT_NONZERO, Violation.SIGNALLED, Violation.TIMEOUT)
    assert backend.exec(["/bin/echo", "alive"]).ok
    backend.stop()


def test_fork_bomb_defused(backend, spec):
    """PID limit MUST bound process creation; the host MUST survive."""
    backend.start(spec)
    code = (
        "import os\n"
        "n=0\nkids=[]\n"
        "for i in range(5000):\n"
        "    try:\n"
        "        p=os.fork()\n"
        "        if p==0: os._exit(0)\n"
        "        kids.append(p); n+=1\n"
        "    except (BlockingIOError, OSError): break\n"
        "import sys\n"
        "for p in kids:\n"
        "    try: os.waitpid(p,0)\n"
        "    except OSError: pass\n"
        "print('FORKED', n)\n")
    result = backend.exec([PY, "-c", code])
    # Whatever happened inside, the sandbox and host MUST remain usable.
    follow_up = backend.exec(["/bin/echo", "alive"])
    assert follow_up.ok
    if "FORKED" in result.stdout:
        forked = int(result.stdout.split("FORKED")[1].split()[0])
        # Bounded: never remotely near the 5000 requested.
        assert forked <= 200, f"fork bomb created {forked} processes"
    backend.stop()


def test_fs_escape_blocked(backend, spec, tmp_path):
    if backend.enforcement < Enforcement.KERNEL:
        pytest.skip("fs allowlist is validation-only without kernel isolation")
    backend.start(spec)
    for target in ("/etc/hostname", "/etc/shadow", "/proc/version"):
        result = backend.exec(["/bin/cat", target])
        assert result.exit_code != 0, f"escape read of {target} succeeded"
    backend.stop()


def test_fs_allowlist_read_write(backend, spec, tmp_path):
    if backend.enforcement < Enforcement.KERNEL:
        pytest.skip("fs allowlist is validation-only without kernel isolation")
    allowed = tmp_path / "note.txt"
    allowed.write_text("inside")
    backend.start(spec)
    read = backend.exec(["/bin/cat", str(allowed)])
    assert read.ok and read.stdout.strip() == "inside"
    write = backend.exec(["/bin/bash", "-c", f"echo more >> {allowed}"])
    assert write.ok
    denied = backend.exec(["/bin/bash", "-c", "echo x > /etc/pwned"])
    assert not denied.ok or backend.exec(["/bin/cat", "/etc/pwned"]).exit_code != 0
    backend.stop()


def test_network_denied(backend, spec):
    if backend.enforcement < Enforcement.KERNEL:
        pytest.skip("network deny requires namespace support")
    backend.start(spec)
    code = ("import socket\n"
            "socket.create_connection(('1.1.1.1', 80), timeout=2)\n"
            "print('NET_OK')\n")
    result = backend.exec([PY, "-c", code])
    assert "NET_OK" not in result.stdout
    code_dns = ("import socket\n"
                "socket.gethostbyname('example.com')\n"
                "print('DNS_OK')\n")
    result = backend.exec([PY, "-c", code_dns])
    assert "DNS_OK" not in result.stdout
    backend.stop()
