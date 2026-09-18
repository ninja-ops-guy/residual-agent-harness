"""Redteam: sandbox escape attempts, scope violations, malicious worker
output. All attacks inert; all asserted blocked-or-observed (K-R1) and
recorded with a FAIL receipt where the receipt system supports it (K-R2).
"""
from __future__ import annotations

import hashlib
import json
import pytest

from residual.core import ContractError, digest
from residual.receipts import StationReceipt
from residual.sandbox import (Enforcement, FsAllowlist, SandboxLimits,
                              SandboxSpec, select_backend)
from residual.verifier import CheckResult

from .attacks import attack_receipt

SANDBOX_PY = "/usr/bin/python3"


@pytest.fixture(scope="module")
def backend():
    return select_backend()


@pytest.fixture()
def spec(tmp_path):
    return SandboxSpec(
        name="redteam",
        fs=FsAllowlist(write=(str(tmp_path),)),
        limits=SandboxLimits(cpu_seconds=15, memory_mb=128, max_pids=25,
                             timeout_seconds=8))


class TestSandboxEscapeAttempts:
    def test_proc_host_read_attempt(self, backend, spec):
        """Attack: read host kernel data via /proc."""
        if backend.enforcement < Enforcement.KERNEL:
            pytest.skip("kernel isolation unavailable")
        backend.start(spec)
        result = backend.exec(["/bin/cat", "/proc/1/cmdline"])
        assert result.exit_code != 0 or b"" == result.stdout.encode()
        observed = backend.exec(["/bin/bash", "-c", "ls /proc | head"])
        # /proc is not even mounted in the jail.
        assert observed.exit_code != 0 or observed.stdout.strip() == ""
        assert attack_receipt("atk-escape-1", "proc host read").verdict is CheckResult.FAIL
        backend.stop()

    def test_ptrace_host_process_attempt(self, backend, spec):
        """Attack: ptrace a host process (should find none / be denied)."""
        if backend.enforcement < Enforcement.KERNEL:
            pytest.skip("kernel isolation unavailable")
        backend.start(spec)
        code = ("import ctypes\n"
                "libc = ctypes.CDLL('libc.so.6', use_errno=True)\n"
                "r = libc.ptrace(16, 1, 0, 0)  # PTRACE_ATTACH host pid 1\n"
                "print('PTRACE_RC', r)\n")
        result = backend.exec([SANDBOX_PY, "-c", code])
        # The probe itself must execute inside the jail; an unavailable host-toolcache
        # interpreter is not evidence that ptrace was denied.
        assert result.exit_code != 127
        assert "PTRACE_RC 0" not in result.stdout
        assert attack_receipt("atk-escape-2", "ptrace host pid 1").verdict is CheckResult.FAIL
        backend.stop()

    def test_write_etc_hosts_attempt(self, backend, spec):
        """Attack: poison /etc/hosts to redirect traffic."""
        if backend.enforcement < Enforcement.KERNEL:
            pytest.skip("kernel isolation unavailable")
        backend.start(spec)
        result = backend.exec(["/bin/bash", "-c",
                               "echo '127.0.0.1 evil.invalid' >> /etc/hosts && echo PWNED"])
        assert "PWNED" not in result.stdout
        assert attack_receipt("atk-escape-3", "etc hosts poison").verdict is CheckResult.FAIL
        backend.stop()


class TestScopeViolations:
    def test_write_outside_allowlist(self, backend, spec):
        """Attack: write outside the granted scope."""
        if backend.enforcement < Enforcement.KERNEL:
            pytest.skip("kernel isolation unavailable")
        backend.start(spec)
        result = backend.exec(["/bin/bash", "-c",
                               "mkdir -p /usr/loot && echo x > /usr/loot/x && echo PWNED"])
        assert "PWNED" not in result.stdout
        assert attack_receipt("atk-scope-1", "write outside allowlist").verdict is CheckResult.FAIL
        backend.stop()

    def test_allowlist_permits_rejects_out_of_scope(self):
        fs = FsAllowlist(read=("/var/data",))
        assert not fs.permits("/var/data-other")
        assert not fs.permits("/var/data/../../etc/passwd")
        assert fs.permits("/var/data/file.txt")
        assert attack_receipt("atk-scope-2", "path traversal probe").verdict is CheckResult.FAIL

    def test_relative_allowlist_entry_rejected(self):
        with pytest.raises(ContractError):
            FsAllowlist(read=("../outside",))


class TestMaliciousWorkerOutput:
    def test_forged_receipt_in_worker_output(self, backend, spec):
        """Attack: worker emits a forged receipt JSON on stdout."""
        backend.start(spec)
        genuine = StationReceipt(
            task_id="task-z", cache_key=hashlib.sha256(b"c").hexdigest(),
            value_hash=digest("vetted"), verifier_name="mechanical:unit",
            verifier_revision=hashlib.sha256(b"r").hexdigest(),
            verdict=CheckResult.PASS)
        forged = genuine.to_dict()
        forged["payload"]["value_hash"] = hashlib.sha256(b"malicious").hexdigest()
        payload = json.dumps(forged)
        result = backend.exec(["/bin/bash", "-c", 'printf "%s\\n" "$1"', "emit", payload])
        assert result.ok  # output captured as data, never executed
        with pytest.raises(ContractError):
            StationReceipt.from_json(result.stdout.strip())
        assert attack_receipt("atk-output-1", "forged receipt on stdout").verdict is CheckResult.FAIL
        backend.stop()

    def test_terminal_escape_output_is_inert_data(self, backend, spec):
        """Attack: ANSI/control spam in worker output must stay inert."""
        backend.start(spec)
        payload = "\\x1b[2J\\x1b[H\\x07" * 100
        result = backend.exec(["/bin/bash", "-c", 'printf "%s\\n" "$1"', "emit", payload])
        assert result.ok
        assert "\\x1b" in result.stdout  # literal text, not interpreted
        assert attack_receipt("atk-output-2", "ansi control spam").verdict is CheckResult.FAIL
        backend.stop()

    def test_oversized_output_capped(self, backend, spec):
        """Attack: memory-exhaust the harness via unbounded stdout."""
        capped = SandboxSpec(
            name="redteam-cap",
            limits=SandboxLimits(cpu_seconds=15, memory_mb=128, max_pids=25,
                                 timeout_seconds=15, max_output_bytes=4096))
        backend.start(capped)
        result = backend.exec(["/bin/bash", "-c", "head -c 10000000 /dev/zero | tr '\\000' A"])
        assert result.exit_code != 127
        assert result.truncated and len(result.stdout) <= 4096
        assert attack_receipt("atk-output-3", "unbounded stdout").verdict is CheckResult.FAIL
        backend.stop()
