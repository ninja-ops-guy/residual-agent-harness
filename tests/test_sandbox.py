"""Unit tests for sandbox specs, backend protocol, and classification."""
from __future__ import annotations

import pytest

from residual.core import ContractError
from residual.sandbox import (BwrapBackend, Enforcement, FsAllowlist,
                              NetworkPolicy, SandboxBackend, SandboxLimits,
                              SandboxSpec, SubprocessBackend, Violation,
                              select_backend)
from residual.sandbox.subprocess_backend import _classify, run_contained
import signal


class TestLimits:
    def test_defaults_conservative(self):
        lim = SandboxLimits()
        assert lim.cpu_seconds <= 60 and lim.memory_mb <= 512
        assert lim.max_pids <= 256 and lim.timeout_seconds <= 120

    @pytest.mark.parametrize("field", ["cpu_seconds", "memory_mb", "max_pids",
                                       "timeout_seconds", "max_output_bytes"])
    def test_zero_rejected(self, field):
        with pytest.raises(ContractError):
            SandboxLimits(**{field: 0})

    def test_negative_rejected(self):
        with pytest.raises(ContractError):
            SandboxLimits(memory_mb=-1)


class TestFsAllowlist:
    def test_relative_path_rejected(self):
        with pytest.raises(ContractError):
            FsAllowlist(read=("etc/passwd",))

    def test_deny_by_default(self):
        fs = FsAllowlist()
        assert not fs.permits("/etc/passwd")

    def test_prefix_matching(self, tmp_path):
        fs = FsAllowlist(read=(str(tmp_path),))
        assert fs.permits(str(tmp_path / "a" / "b.txt"))
        assert not fs.permits(str(tmp_path) + "-sibling")
        assert not fs.permits("/etc/hostname")

    def test_write_requires_write_entry(self, tmp_path):
        fs = FsAllowlist(read=(str(tmp_path),))
        assert not fs.permits(str(tmp_path / "x"), write=True)
        fs2 = FsAllowlist(write=(str(tmp_path),))
        assert fs2.permits(str(tmp_path / "x"), write=True)
        assert fs2.permits(str(tmp_path / "x"))  # write implies read


class TestNetworkSpec:
    def test_default_deny(self):
        assert SandboxSpec(name="t").network is NetworkPolicy.DENY

    def test_proxy_requires_allowlist(self):
        with pytest.raises(ContractError):
            SandboxSpec(name="t", network=NetworkPolicy.PROXY,
                        proxy_host="127.0.0.1", proxy_port=8080)

    def test_proxy_requires_endpoint(self):
        with pytest.raises(ContractError):
            SandboxSpec(name="t", network=NetworkPolicy.PROXY,
                        proxy_allowlist=("example.com",))

    def test_proxy_ok(self):
        spec = SandboxSpec(name="t", network=NetworkPolicy.PROXY,
                           proxy_host="127.0.0.1", proxy_port=8080,
                           proxy_allowlist=("example.com",))
        assert spec.proxy_allowlist == ("example.com",)

    def test_allow_network_rejected_by_backend(self):
        backend = SubprocessBackend()
        with pytest.raises(ContractError):
            backend.start(SandboxSpec(name="t", network=NetworkPolicy.ALLOW))


class TestProtocol:
    def test_subprocess_backend_satisfies_protocol(self):
        assert isinstance(SubprocessBackend(), SandboxBackend)

    def test_bwrap_backend_satisfies_protocol(self):
        assert isinstance(BwrapBackend(), SandboxBackend)

    def test_select_backend_graceful(self):
        backend = select_backend()
        assert isinstance(backend, SandboxBackend)
        if not BwrapBackend.available():
            assert isinstance(backend, SubprocessBackend)

    def test_exec_requires_start(self):
        with pytest.raises(RuntimeError):
            SubprocessBackend().exec(["/bin/true"])

    def test_stop_idempotent(self):
        backend = select_backend()
        backend.stop()  # never started: MUST NOT raise
        backend.start(SandboxSpec(name="t"))
        backend.stop()
        backend.stop()

    def test_enforcement_declared(self):
        backend = select_backend()
        assert backend.enforcement in (Enforcement.KERNEL, Enforcement.BEST_EFFORT)
        if BwrapBackend.available():
            assert backend.enforcement is Enforcement.KERNEL


class TestBwrapArgv:
    def test_wrap_maps_policy(self, tmp_path):
        backend = BwrapBackend()
        spec = SandboxSpec(name="t", fs=FsAllowlist(read=("/etc",),
                                                    write=(str(tmp_path),)))
        backend.start(spec)
        argv = backend._wrap(["/bin/echo", "hi"])
        assert argv[0] == "bwrap" and "--die-with-parent" in argv
        assert "--unshare-net" in argv  # DENY default
        joined = " ".join(argv)
        assert "--ro-bind /etc /etc" in joined
        assert f"--bind {tmp_path} {tmp_path}" in joined

    def test_classify(self):
        assert _classify(0, False) == (0, None, Violation.NONE)
        assert _classify(3, False)[2] is Violation.EXIT_NONZERO
        assert _classify(-signal.SIGSEGV, False)[2] is Violation.SIGNALLED
        assert _classify(-signal.SIGXCPU, False)[2] is Violation.CPU_LIMIT
        assert _classify(-signal.SIGKILL, True)[2] is Violation.TIMEOUT


class TestCapture:
    def test_output_cap(self):
        from residual.sandbox.spec import SandboxLimits
        spec = SandboxSpec(name="t", limits=SandboxLimits(max_output_bytes=64))
        result = run_contained(["/usr/bin/head", "-c", "10000", "/dev/zero"],
                               spec)
        assert result.truncated and len(result.stdout) <= 64

    def test_crash_never_propagates(self):
        spec = SandboxSpec(name="t")
        for argv in (["/bin/bash", "-c", "exit 9"],
                     ["/bin/bash", "-c", "kill -KILL $$"]):
            result = run_contained(argv, spec)  # MUST NOT raise
            assert not result.ok
