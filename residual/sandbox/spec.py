"""Sandbox specifications: limits, filesystem allowlists, network policy.

Requirement IDs (track B):
  B-R1: A sandbox spec MUST declare explicit resource limits (CPU seconds,
        memory MB, PID count) and a wall-clock timeout; unspecified fields
        MUST default to conservative values, never to "unlimited".
  B-R2: A filesystem allowlist MUST be deny-by-default: paths not on the
        allowlist MUST NOT be readable by sandboxed code when the active
        backend supports kernel-level isolation, and MUST be rejected at
        validation time in every backend.
  B-R3: Network policy MUST default to DENY. A proxy policy MUST carry an
        explicit host allowlist; an empty allowlist with PROXY mode is a
        contract error.
  B-R4: Sandbox results MUST capture nonzero exits, signals, timeouts, and
        resource violations as data; they MUST NOT propagate as exceptions
        from ``exec``.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from pathlib import Path

from ..core import ContractError, identifier, positive_int


class NetworkPolicy(str, enum.Enum):
    """Egress policy for sandboxed code."""
    DENY = "deny"      # no network namespace connectivity at all
    PROXY = "proxy"    # egress only via an allowlisted HTTP proxy
    ALLOW = "allow"    # unrestricted (MUST be opted into explicitly)


class Violation(str, enum.Enum):
    NONE = "none"
    EXIT_NONZERO = "exit-nonzero"
    SIGNALLED = "signalled"
    TIMEOUT = "timeout"
    CPU_LIMIT = "cpu-limit"
    MEMORY_LIMIT = "memory-limit"
    PID_LIMIT = "pid-limit"
    FS_ESCAPE = "fs-escape"
    NETWORK = "network"
    START_FAILED = "start-failed"


# Defaults are deliberately conservative (B-R1).
DEFAULT_CPU_SECONDS = 30
DEFAULT_MEMORY_MB = 256
DEFAULT_MAX_PIDS = 64
DEFAULT_TIMEOUT_SECONDS = 60
DEFAULT_OUTPUT_BYTES = 1 << 20  # 1 MiB capture cap


@dataclass(frozen=True)
class SandboxLimits:
    """Hard resource envelope. Zero/None means "use default", not unlimited."""
    cpu_seconds: int = DEFAULT_CPU_SECONDS
    memory_mb: int = DEFAULT_MEMORY_MB
    max_pids: int = DEFAULT_MAX_PIDS
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    max_output_bytes: int = DEFAULT_OUTPUT_BYTES

    def __post_init__(self):
        positive_int(self.cpu_seconds, "cpu_seconds")
        positive_int(self.memory_mb, "memory_mb")
        positive_int(self.max_pids, "max_pids")
        positive_int(self.timeout_seconds, "timeout_seconds")
        positive_int(self.max_output_bytes, "max_output_bytes")
        if self.memory_mb > 1 << 20:
            raise ContractError("memory_mb is implausibly large")


@dataclass(frozen=True)
class FsAllowlist:
    """Deny-by-default filesystem allowlist (B-R2).

    ``read`` paths are mounted/readable inside the sandbox; ``write`` paths
    are additionally writable. All entries MUST be absolute, existent,
    symlink-resolved host paths.
    """
    read: tuple[str, ...] = ()
    write: tuple[str, ...] = ()

    def __post_init__(self):
        for group, paths in (("read", self.read), ("write", self.write)):
            if not isinstance(paths, (tuple, list)):
                raise ContractError(f"fs allowlist {group} must be a sequence")
            for p in paths:
                if not isinstance(p, str) or not p.startswith("/"):
                    raise ContractError(f"fs allowlist {group} entry must be absolute: {p!r}")
                resolved = str(Path(p).resolve())
                if resolved != p.rstrip("/") and resolved != p:
                    raise ContractError(f"fs allowlist entry must be pre-resolved: {p!r}")
        object.__setattr__(self, "read", tuple(dict.fromkeys(self.read)))
        object.__setattr__(self, "write", tuple(dict.fromkeys(self.write)))

    def permits(self, path: str, *, write: bool = False) -> bool:
        """True iff ``path`` (already resolved) is covered by the allowlist."""
        p = str(Path(path).resolve())
        allowed = self.write if write else self.read + self.write
        return any(p == a or p.startswith(a.rstrip("/") + "/") for a in allowed)


@dataclass(frozen=True)
class SandboxSpec:
    """Complete sandbox request. Network defaults to DENY (B-R3)."""
    name: str
    limits: SandboxLimits = field(default_factory=SandboxLimits)
    fs: FsAllowlist = field(default_factory=FsAllowlist)
    network: NetworkPolicy = NetworkPolicy.DENY
    proxy_host: str = ""
    proxy_port: int = 0
    proxy_allowlist: tuple[str, ...] = ()
    workdir: str = "/"
    env: tuple[tuple[str, str], ...] = ()

    def __post_init__(self):
        identifier(self.name)
        object.__setattr__(self, "network", NetworkPolicy(self.network))
        if self.network is NetworkPolicy.PROXY:
            if not self.proxy_allowlist:
                raise ContractError("PROXY policy requires a nonempty proxy_allowlist")
            if not self.proxy_host or not (1 <= self.proxy_port <= 65535):
                raise ContractError("PROXY policy requires proxy_host and proxy_port")
        for host in self.proxy_allowlist:
            identifier(host)
        if not self.workdir.startswith("/"):
            raise ContractError("workdir must be absolute")
        for key, value in self.env:
            if not isinstance(key, str) or not key or "=" in key:
                raise ContractError("invalid sandbox env key")
            if not isinstance(value, str):
                raise ContractError("invalid sandbox env value")


@dataclass(frozen=True)
class SandboxResult:
    """Outcome of one exec. Every failure mode is data (B-R4)."""
    exit_code: int | None
    signal: int | None
    timed_out: bool
    violation: Violation
    stdout: str
    stderr: str
    duration_seconds: float
    truncated: bool = False

    @property
    def ok(self) -> bool:
        return (self.exit_code == 0 and self.signal is None and not self.timed_out
                and self.violation is Violation.NONE)
