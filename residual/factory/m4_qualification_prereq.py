"""M4 qualification runner prerequisites: capability probes + environment manifest.

This module is the fail-closed *prerequisite gate* for M4 qualification (the
mechanism intended by draft PR #88). It answers one question, with typed,
machine-readable evidence: can this environment run the isolated M4 verifier
(:mod:`residual.factory.m4_sandbox`, profile ``linux-userns-isolated-v1``)?

Design rules:

* Probes use the **same mechanism** as the sandbox itself — the ``unshare``
  argv built by :func:`residual.factory.m4_sandbox._unshare_argv` — plus
  per-capability probes so a BLOCKED report names the missing capability
  instead of collapsing to a single ``namespace_probe_failed``.
* The report is explicit: overall ``PASS`` only when **every** required
  capability passes; otherwise ``BLOCKED``. Nothing is silently skipped.
* An environment manifest (OS, kernel, userns sysctls, Python pin, resource
  limits, dependency versions) is captured as retained evidence alongside the
  probe results.

This module changes no sandbox behaviour and performs no qualification by
itself: final M4 qualification additionally requires the repaired runtime
tracked by issue #108 and the execution gate of PR #88.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import resource
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from .m4_sandbox import SANDBOX_PROFILE, _unshare_argv, probe_isolation, run_isolated

REPORT_SCHEMA = "m4-qualification-prereq-report-v1"

# Python versions pinned for M4 qualification runs (major.minor). The factory
# execution workflow runs 3.12; qualification evidence must name its Python.
PINNED_PYTHON = ("3.12",)

# Runtime dependencies the isolated verifier path imports (with the minimum
# versions declared in pyproject [project.optional-dependencies].factory).
REQUIRED_DEPENDENCIES = {
    "cryptography": "43",
    "yaml": "6",  # PyYAML
}

_PROBE_TIMEOUT_S = 30


@dataclass(frozen=True)
class CapabilityResult:
    """Typed outcome of one capability probe. ``status`` is pass|blocked."""

    name: str
    status: str  # "pass" | "blocked"
    detail: str
    probe_argv: tuple[str, ...] = ()
    returncode: int | None = None


def _run_unshare(flags: tuple[str, ...], inner: tuple[str, ...]) -> CapabilityResult:
    """Probe one capability via unshare; never raises, never skips."""
    base = _unshare_argv(list(inner))
    name = flags[0].lstrip("-").replace("-", "_") if flags else "composite"
    if base is None:
        return CapabilityResult(name, "blocked", "unshare_binary_missing")
    # base = [unshare, <full sandbox flags>, --, inner]; rebuild with only the
    # requested flags so each capability is isolated in the report. The user
    # namespace + root mapping is always included first (mirrors the sandbox:
    # mount/pid/net/ipc/uts namespaces are entered as the userns-mapped root).
    binary = base[0]
    argv = (binary, "--user", "--map-root-user", *flags, "--", *inner)
    try:
        result = subprocess.run(
            list(argv), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE, timeout=_PROBE_TIMEOUT_S, check=False,
            env={"PATH": "/usr/bin:/bin"},
        )
    except subprocess.TimeoutExpired:
        return CapabilityResult(name, "blocked", "probe_timeout", argv, None)
    except OSError as exc:
        return CapabilityResult(name, "blocked", f"probe_launch_failed:{type(exc).__name__}", argv, None)
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", "replace").strip().splitlines()
        tail = stderr[-1] if stderr else "no stderr"
        return CapabilityResult(name, "blocked", f"probe_failed:{tail}", argv, result.returncode)
    return CapabilityResult(name, "pass", "ok", argv, result.returncode)


def probe_capabilities() -> list[CapabilityResult]:
    """Run every prerequisite probe. BLOCKED on any missing capability."""
    results: list[CapabilityResult] = []

    if sys.platform == "linux" and os.name == "posix":
        results.append(CapabilityResult("platform_linux", "pass", platform.platform()))
    else:
        results.append(CapabilityResult("platform_linux", "blocked", f"platform_not_linux:{sys.platform}"))

    if hasattr(os, "chroot"):
        results.append(CapabilityResult("chroot_available", "pass", "os.chroot present"))
    else:
        results.append(CapabilityResult("chroot_available", "blocked", "chroot_unavailable"))

    unshare = shutil.which("unshare", path="/usr/bin:/bin")
    if unshare is None:
        results.append(CapabilityResult("unshare_binary", "blocked", "unshare_binary_missing"))
        # Without unshare every namespace probe is blocked, not skipped.
        for name in ("user_namespace", "mount_namespace", "pid_namespace",
                     "network_namespace", "ipc_namespace", "uts_namespace",
                     "kill_child", "composite_sandbox_profile", "isolated_execution"):
            results.append(CapabilityResult(name, "blocked", "unshare_binary_missing"))
        return results
    results.append(CapabilityResult("unshare_binary", "pass", unshare))

    # Per-capability probes, each inside a user namespace with root mapping
    # exactly as m4_sandbox composes them.
    results.append(_namespace_probe("user_namespace", (), ("/usr/bin/env", "-i", "sh", "-c", "true")))
    results.append(_namespace_probe("mount_namespace", ("--mount",), ("/usr/bin/env", "-i", "sh", "-c", "true")))
    results.append(_namespace_probe("pid_namespace", ("--pid", "--fork"), ("/usr/bin/env", "-i", "sh", "-c", "true")))
    results.append(_namespace_probe("network_namespace", ("--net",), ("/usr/bin/env", "-i", "sh", "-c", "true")))
    results.append(_namespace_probe("ipc_namespace", ("--ipc",), ("/usr/bin/env", "-i", "sh", "-c", "true")))
    results.append(_namespace_probe("uts_namespace", ("--uts",), ("/usr/bin/env", "-i", "sh", "-c", "true")))
    results.append(_namespace_probe(
        "kill_child", ("--kill-child", "--pid", "--fork"),
        ("/usr/bin/env", "-i", "sh", "-c", "sleep 5 & exec true")))

    # Composite probe: the sandbox's own fail-closed probe, same argv.
    ok, reason = probe_isolation()
    results.append(CapabilityResult(
        "composite_sandbox_profile", "pass" if ok else "blocked",
        f"{SANDBOX_PROFILE}:{reason}",
        tuple(_unshare_argv(["/usr/bin/env", "-i", "sh", "-c", "true"]) or ())))
    results.append(probe_execution())
    return results


def probe_execution() -> CapabilityResult:
    """Exercise the actual verifier path, including setup and candidate exec.

    Namespace availability alone does not establish that the chroot, resource
    limits, readiness handshake and child executable can all run. This is a
    prerequisite smoke check, not containment/security qualification.
    """
    marker = b"m4-prerequisite-execution\n"
    argv = ("/usr/bin/python3", "-c", f"import sys; sys.stdout.write({marker.decode()!r})")
    try:
        with tempfile.TemporaryDirectory(prefix="m4-prereq-worktree-") as worktree:
            result = run_isolated(argv, Path(worktree), timeout_s=20, output_limit=4096)
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        return CapabilityResult("isolated_execution", "blocked",
                                f"execution_probe_failed:{type(exc).__name__}", argv)
    passed = (result.status == "pass" and result.returncode == 0
              and result.reason == "exit" and result.execution_boundary == SANDBOX_PROFILE
              and result.stdout_sha256 == hashlib.sha256(marker).hexdigest()
              and result.stderr_sha256 == hashlib.sha256(b"").hexdigest())
    return CapabilityResult(
        "isolated_execution", "pass" if passed else "blocked",
        json.dumps(asdict(result), sort_keys=True), argv, result.returncode)


def _namespace_probe(name: str, flags: tuple[str, ...], inner: tuple[str, ...]) -> CapabilityResult:
    r = _run_unshare(flags, inner)
    return CapabilityResult(name, r.status, r.detail, r.probe_argv, r.returncode)


def _read_sysctl(path: str) -> str | None:
    try:
        return Path(path).read_text().strip()
    except OSError:
        return None


def _dependency_versions() -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for module, minimum in REQUIRED_DEPENDENCIES.items():
        try:
            mod = __import__(module)
            version = getattr(mod, "__version__", "unknown")
            try:
                ok = int(version.split(".")[0]) >= int(minimum)
            except (AttributeError, TypeError, ValueError):
                ok = False
            out[module] = {
                "status": "pass" if ok else "blocked",
                "version": version,
                "minimum_major": minimum,
            }
        except ImportError:
            out[module] = {"status": "blocked", "version": None, "minimum_major": minimum}
    return out


def collect_manifest() -> dict:
    """Capture the reproducible-environment manifest as retained evidence."""
    python_version = platform.python_version()
    py_mm = ".".join(python_version.split(".")[:2])
    deps = _dependency_versions()
    rlimits = {}
    for name in ("RLIMIT_AS", "RLIMIT_CPU", "RLIMIT_NOFILE", "RLIMIT_NPROC"):
        res = getattr(resource, name, None)
        if res is not None:
            soft, hard = resource.getrlimit(res)
            rlimits[name] = {"soft": soft, "hard": hard}
    return {
        "schema": "m4-qualification-env-manifest-v1",
        "captured_at_unix": int(time.time()),
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "platform": platform.platform(),
        },
        "kernel": {
            "max_user_namespaces": _read_sysctl("/proc/sys/user/max_user_namespaces"),
            "unprivileged_userns_clone": _read_sysctl("/proc/sys/kernel/unprivileged_userns_clone"),
            "unprivileged_userns_apparmor_policy": _read_sysctl(
                "/proc/sys/kernel/unprivileged_userns_apparmor_policy"),
        },
        "python": {
            "version": python_version,
            "executable": sys.executable,
            "pinned": list(PINNED_PYTHON),
            "status": "pass" if py_mm in PINNED_PYTHON else "blocked",
        },
        "resource_limits": rlimits,
        "cpu_count": os.cpu_count(),
        "dependencies": deps,
    }


def build_report(*, revision: str | None = None) -> dict:
    """Build the explicit PASS/BLOCKED prerequisite report."""
    capabilities = probe_capabilities()
    manifest = collect_manifest()
    blocked = [c.name for c in capabilities if c.status != "pass"]
    if manifest["python"]["status"] != "pass":
        blocked.append("python_pin")
    blocked += [f"dependency:{m}" for m, d in manifest["dependencies"].items()
                if d["status"] != "pass"]
    return {
        "schema": REPORT_SCHEMA,
        "overall": "PASS" if not blocked else "BLOCKED",
        "blocked_capabilities": blocked,
        "sandbox_profile": SANDBOX_PROFILE,
        "revision": revision or os.environ.get("GITHUB_SHA") or None,
        "capabilities": [asdict(c) for c in capabilities],
        "environment_manifest": manifest,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="M4 qualification prerequisite probe: emits an explicit "
                    "PASS/BLOCKED JSON report. Exit 0 on PASS, 1 on BLOCKED.")
    parser.add_argument("--output", type=Path, default=None,
                        help="write the JSON report to this path")
    parser.add_argument("--revision", default=None,
                        help="tested revision SHA to bind the evidence to")
    args = parser.parse_args(argv)
    report = build_report(revision=args.revision)
    text = json.dumps(report, indent=2, sort_keys=True)
    print(text)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n")
    return 0 if report["overall"] == "PASS" else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
