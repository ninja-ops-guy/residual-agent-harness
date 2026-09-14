"""bubblewrap (bwrap) sandbox backend.

Requirement IDs (track B):
  B-R8: When bwrap is present it MUST be preferred: it provides kernel
        mount/network/PID namespaces with die-with-parent semantics.
  B-R9: The bwrap backend MUST map SandboxLimits onto bwrap flags:
        --unshare-net for DENY, --ro-bind for fs read allowlist entries,
        --bind for write entries, and MUST NOT widen mounts beyond the
        allowlist plus a minimal runtime root (/usr, /lib, /bin, /sbin).
"""
from __future__ import annotations

import shutil

from .backend import Enforcement
from .spec import FsAllowlist, NetworkPolicy, SandboxResult, SandboxSpec
from .subprocess_backend import run_contained

# Minimal runtime root so dynamically linked binaries work inside the jail.
_RUNTIME_BINDS = ("/usr", "/lib", "/lib64", "/bin", "/sbin", "/etc/ld.so.cache")


class BwrapBackend:
    name = "bwrap"
    enforcement = Enforcement.KERNEL

    def __init__(self):
        self._spec: SandboxSpec | None = None

    @staticmethod
    def available() -> bool:
        return shutil.which("bwrap") is not None

    def start(self, spec: SandboxSpec) -> None:
        self._spec = spec

    def _wrap(self, argv: list[str]) -> list[str]:
        assert self._spec is not None
        spec = self._spec
        cmd = ["bwrap", "--die-with-parent", "--new-session", "--unshare-pid"]
        if spec.network is NetworkPolicy.DENY:
            cmd.append("--unshare-net")
        import os
        for src in _RUNTIME_BINDS:
            if os.path.exists(src):
                cmd += ["--ro-bind", src, src]
        cmd += ["--tmpfs", "/tmp"]
        for path in spec.fs.read:
            cmd += ["--ro-bind", path, path]
        for path in spec.fs.write:
            cmd += ["--bind", path, path]
        cmd += ["--chdir", spec.workdir, "--"]
        return cmd + argv

    def exec(self, argv: list[str], *, stdin: str = "") -> SandboxResult:
        if self._spec is None:
            raise RuntimeError("sandbox not started")
        return run_contained(self._wrap(argv), self._spec, stdin=stdin)

    def stop(self) -> None:
        self._spec = None
