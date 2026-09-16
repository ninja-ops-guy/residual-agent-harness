"""Residual sandbox: containment for untrusted worker code (track B).

RFC 2119 requirements B-R1 .. B-R16 are declared in:
  - spec.py               (limits, fs allowlist, network policy, results)
  - backend.py            (SandboxBackend protocol, graceful selection)
  - bwrap.py              (bubblewrap backend, preferred when present)
  - subprocess_backend.py (rlimits + namespace-launcher fallback)
  - _nslaunch.py          (user/mount/pid/net namespace launcher)

Summary of MUSTs:
  - Limits are mandatory and default to conservative values (B-R1).
  - Filesystem allowlists are deny-by-default (B-R2).
  - Network policy defaults to DENY (B-R3).
  - Crashes (nonzero exit, signal, timeout) are captured, never raised (B-R4).
  - Backend selection degrades bwrap -> namespaces -> restricted subprocess
    and honestly reports its enforcement level (B-R6, B-R11, B-R12).

Honest limitations in this environment: bwrap is absent and cgroup v2 is
unavailable (cgroup v1 hierarchy mounted read-only), so CPU/memory/PID
limits are enforced with setrlimit (RLIMIT_CPU/AS/NPROC) instead of
cgroups; RLIMIT_NPROC counts per-UID, so it is a conservative cap shared
with the host user's other processes.
"""
from .backend import Enforcement, SandboxBackend, select_backend
from .bwrap import BwrapBackend
from .spec import (FsAllowlist, NetworkPolicy, SandboxLimits, SandboxResult,
                   SandboxSpec, Violation)
from .subprocess_backend import SubprocessBackend

__all__ = ["Enforcement", "FsAllowlist", "NetworkPolicy", "SandboxBackend",
           "SandboxLimits", "SandboxResult", "SandboxSpec", "Violation",
           "BwrapBackend", "SubprocessBackend", "select_backend"]
