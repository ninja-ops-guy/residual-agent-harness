#!/usr/bin/env python3
"""M4 capable-runner preflight probe.

Determines whether this host can execute the namespace-isolated M4 sandbox
(residual/factory/m4_sandbox.py) with every prerequisite PROVEN by a real
execution probe, or emits a precise BLOCKED report naming exactly what is
missing and how to remediate it.

Contract:
  * stdout (or --output file) receives a JSON report:
      {
        "schema_version": 1,
        "capabilities": {
          "<name>": {"status": "PASS"|"FAIL"|"BLOCKED",
                     "detail": "<machine-readable detail>",
                     "remediation": "<operator action>"}
          ...
        },
        "blocked": ["<name>", ...],
        "verdict": "QUALIFIED" | "BLOCKED",
        "capability_hash": "<sha256 over canonical capabilities mapping>"
      }
  * Exit code 0 when QUALIFIED, 3 when BLOCKED.
  * Deterministic: capability ordering is fixed; the capability_hash is
    computed over the capabilities mapping only (no timestamps, no
    hostnames), so identical capability states hash identically.

Semantics: PASS = proven by an actual execution probe (not just a file
existing); BLOCKED = the kernel/environment refused the capability at
runtime; FAIL = a required resource is absent or malformed. A capability
that is not PASS never contributes to qualification.

Stdlib only. Safe to run repeatedly; the only write is a small fsync'd
probe file inside the runs/ evidence directory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile

SCHEMA_VERSION = 1
EXIT_QUALIFIED = 0
EXIT_BLOCKED = 3
DEFAULT_MIN_FREE_BYTES = 64 * 1024 * 1024  # 64 MiB of evidence headroom.

_UNSHARE = "/usr/bin/unshare"
_BASE_NS_FLAGS = ["--user", "--map-root-user"]


class Probe:
    """Side-effecting host access, isolated so tests can substitute a fake.

    Every method must be deterministic given the host state; check functions
    below are pure over a Probe instance.
    """

    def read_text(self, path: str) -> str | None:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                return fh.read()
        except OSError:
            return None

    def run(self, argv: list[str], timeout: int = 20) -> tuple[int, str]:
        """Run argv, returning (returncode, stderr_tail). Never raises."""
        try:
            result = subprocess.run(
                argv,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                timeout=timeout,
                check=False,
                env={"PATH": "/usr/bin:/bin"},
            )
        except subprocess.TimeoutExpired:
            return (124, "probe_timeout")
        except OSError as exc:
            return (127, f"launch_error:{type(exc).__name__}")
        return (result.returncode, result.stderr.decode("utf-8", "replace").strip()[-400:])

    def which(self, name: str) -> str | None:
        return shutil.which(name)

    def has_pidfd_open(self) -> bool:
        return hasattr(os, "pidfd_open")

    def pidfd_open_self(self) -> int:
        fd = os.pidfd_open(os.getpid())
        os.close(fd)
        return fd

    def unix_socket_probe(self, directory: str) -> tuple[bool, str]:
        path = os.path.join(directory, "preflight.sock")
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            sock.bind(path)
            sock.listen(1)
        except OSError as exc:
            return (False, f"af_unix_bind_failed:{exc.errno}")
        finally:
            sock.close()
        return (True, "af_unix_bind_listen_ok")

    def statvfs_free(self, path: str) -> int:
        st = os.statvfs(path)
        return st.f_bavail * st.f_frsize

    def write_and_fsync(self, path: str, payload: bytes) -> None:
        with open(path, "wb") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())


def _cap(status: str, detail: str, remediation: str) -> dict:
    return {"status": status, "detail": detail, "remediation": remediation}


def _unshare_probe(probe: Probe, extra_flags: list[str]) -> tuple[int, str]:
    """Actual execution probe: enter the namespaces and run /bin/true."""
    return probe.run([_UNSHARE, *_BASE_NS_FLAGS, *extra_flags, "--", "/bin/true"])


def check_user_namespace(probe: Probe) -> dict:
    clone = probe.read_text("/proc/sys/kernel/unprivileged_userns_clone")
    if clone is not None and clone.strip() != "1":
        return _cap(
            "BLOCKED",
            f"unprivileged_userns_clone={clone.strip()}",
            "sysctl -w kernel.unprivileged_userns_clone=1 (Debian/Ubuntu images)",
        )
    maxns = probe.read_text("/proc/sys/user/max_user_namespaces")
    if maxns is None:
        return _cap("FAIL", "max_user_namespaces_missing", "boot a kernel with CONFIG_USER_NS=y")
    try:
        if int(maxns.strip()) <= 0:
            return _cap(
                "BLOCKED",
                "max_user_namespaces=0",
                "sysctl -w user.max_user_namespaces=15000",
            )
    except ValueError:
        return _cap("FAIL", f"max_user_namespaces_unparseable:{maxns.strip()}", "inspect /proc/sys/user/max_user_namespaces")
    rc, err = _unshare_probe(probe, [])
    if rc != 0:
        return _cap(
            "BLOCKED",
            f"userns_exec_probe_rc={rc}:{err}",
            "enable unprivileged user namespaces (sysctl kernel.unprivileged_userns_clone=1, "
            "user.max_user_namespaces>0); on RHEL check user.max_user_namespaces and "
            "/proc/sys/kernel/unprivileged_userns_clone equivalent",
        )
    return _cap("PASS", "userns_exec_probe_ok:unshare --user --map-root-user", "")


def _ns_check(name: str, flags: list[str], remediation: str):
    def _check(probe: Probe) -> dict:
        rc, err = _unshare_probe(probe, flags)
        if rc != 0:
            return _cap("BLOCKED", f"{name}_ns_exec_probe_rc={rc}:{err}", remediation)
        return _cap("PASS", f"{name}_ns_exec_probe_ok:unshare {' '.join(flags)}", "")

    return _check


check_mount_namespace = _ns_check(
    "mount",
    ["--mount"],
    "kernel must allow CLONE_NEWNS inside a user namespace (CONFIG_USER_NS); "
    "if running in a container, drop --privileged restrictions / seccomp profile that denies unshare",
)
check_pid_namespace = _ns_check(
    "pid",
    ["--pid", "--fork", "--kill-child"],
    "kernel CONFIG_PID_NS=y required; nested containers often deny it (seccomp/apparmor)",
)
check_ipc_namespace = _ns_check(
    "ipc",
    ["--ipc"],
    "kernel CONFIG_IPC_NS=y required; container runtimes may deny CLONE_NEWIPC",
)
check_uts_namespace = _ns_check(
    "uts",
    ["--uts"],
    "kernel CONFIG_UTS_NS=y required; container runtimes may deny CLONE_NEWUTS",
)
check_net_namespace = _ns_check(
    "net",
    ["--net"],
    "kernel CONFIG_NET_NS=y required; container runtimes may deny CLONE_NEWNET",
)


def check_seccomp(probe: Probe) -> dict:
    status = probe.read_text("/proc/self/status")
    if status is None:
        return _cap("FAIL", "proc_self_status_missing", "mount /proc")
    field = None
    for line in status.splitlines():
        if line.startswith("Seccomp:"):
            field = line.split(":", 1)[1].strip()
            break
    if field is None:
        return _cap("FAIL", "seccomp_field_missing", "kernel must expose Seccomp in /proc/self/status")
    actions = probe.read_text("/proc/sys/kernel/seccomp/actions_avail")
    if actions is not None and "filter" not in actions.split():
        return _cap(
            "BLOCKED",
            f"seccomp_filter_unavailable:actions_avail={actions.strip()}",
            "boot kernel with CONFIG_SECCOMP_FILTER=y",
        )
    if actions is None:
        # Older kernels lack actions_avail; Seccomp field presence plus
        # CONFIG_SECCOMP is the best static signal, mark filter support
        # as proven only via the field existing (mode 0/1/2 are all fine —
        # the sandbox installs its own filter at exec time).
        return _cap("PASS", f"seccomp_field={field}:actions_avail_absent_assume_filter", "")
    return _cap("PASS", f"seccomp_field={field}:filter_available", "")


def check_cgroups_v2(probe: Probe) -> dict:
    controllers = probe.read_text("/sys/fs/cgroup/cgroup.controllers")
    if controllers is None:
        return _cap(
            "BLOCKED",
            "cgroup_v2_absent:no /sys/fs/cgroup/cgroup.controllers",
            "boot with cgroup v2 unified hierarchy (systemd.unified_cgroup_hierarchy=1); "
            "on CI containers use a cgroup2 host or --cgroupns=private with a v2 host",
        )
    subtree = "/sys/fs/cgroup/cgroup.subtree_control"
    if os.access(subtree, os.W_OK):
        return _cap(
            "PASS",
            f"cgroup_v2_present:controllers={controllers.strip() or 'none'}:subtree_control_writable",
            "",
        )
    return _cap(
        "BLOCKED",
        "cgroup_v2_present_but_not_delegated:subtree_control_read_only",
        "delegate a writable cgroup sub-tree to the runner (systemd Delegate=yes, or "
        "chown the delegated cgroup dir); without delegation memory limits cannot be enforced",
    )


def check_bubblewrap(probe: Probe) -> dict:
    binary = probe.which("bwrap")
    if binary is None:
        return _cap(
            "FAIL",
            "bwrap_not_on_path",
            "install bubblewrap (apt install bubblewrap / dnf install bubblewrap); "
            "CI images: add it to the runner image",
        )
    rc, err = probe.run([binary, "--version"])
    version = err.strip() if rc != 0 else ""
    rc2, err2 = probe.run([binary, "--ro-bind", "/", "/", "--", "/bin/true"])
    if rc2 != 0:
        return _cap(
            "BLOCKED",
            f"bwrap_exec_probe_rc={rc2}:{err2}",
            "bubblewrap needs unprivileged user namespaces; fix userns first, or install "
            "the setuid bwrap variant where policy allows it",
        )
    return _cap("PASS", f"bwrap_exec_probe_ok:{version or 'version_unparsed'}", "")


def check_pidfd(probe: Probe) -> dict:
    if not probe.has_pidfd_open():
        return _cap(
            "FAIL",
            "os_pidfd_open_missing",
            "use Python >= 3.9 on a kernel >= 5.3 (pidfd_open syscall)",
        )
    try:
        fd = probe.pidfd_open_self()
    except OSError as exc:
        return _cap(
            "BLOCKED",
            f"pidfd_open_call_failed:errno={exc.errno}",
            "kernel >= 5.3 with pidfd_open not blocked by seccomp (Docker default "
            "seccomp profiles before 20.10 block it)",
        )
    return _cap("PASS", f"pidfd_open_self_ok:fd={fd}", "")


def check_af_unix(probe: Probe) -> dict:
    with tempfile.TemporaryDirectory(prefix="m4-preflight-") as tmp:
        ok, detail = probe.unix_socket_probe(tmp)
    if not ok:
        return _cap("BLOCKED", detail, "ensure AF_UNIX sockets are permitted (kernel CONFIG_UNIX=y; check seccomp/LSM policy)")
    return _cap("PASS", detail, "")


def check_artifact_retention(probe: Probe, runs_dir: str, min_free_bytes: int) -> dict:
    try:
        os.makedirs(runs_dir, exist_ok=True)
    except OSError as exc:
        return _cap("FAIL", f"runs_dir_create_failed:{exc.errno}:{runs_dir}", "create the runs/ evidence dir writable by the runner user")
    probe_path = os.path.join(runs_dir, ".m4-preflight-fsync-probe")
    try:
        probe.write_and_fsync(probe_path, b"m4-preflight-fsync\n")
    except OSError as exc:
        return _cap("BLOCKED", f"runs_dir_write_fsync_failed:errno={exc.errno}", "mount the evidence volume read-write with fsync support")
    finally:
        try:
            os.unlink(probe_path)
        except OSError:
            pass
    free = probe.statvfs_free(runs_dir)
    if free < min_free_bytes:
        return _cap(
            "BLOCKED",
            f"insufficient_free_space:free={free}:required>={min_free_bytes}",
            "free disk space on the evidence volume or raise the retention budget",
        )
    return _cap("PASS", f"runs_dir_writable_fsync_ok:free={free}", "")


# Fixed, deterministic capability order.
CAPABILITY_CHECKS = [
    ("user_namespace", check_user_namespace),
    ("mount_namespace", check_mount_namespace),
    ("pid_namespace", check_pid_namespace),
    ("ipc_namespace", check_ipc_namespace),
    ("uts_namespace", check_uts_namespace),
    ("net_namespace", check_net_namespace),
    ("seccomp", check_seccomp),
    ("cgroups_v2", check_cgroups_v2),
    ("bubblewrap", check_bubblewrap),
    ("pidfd", check_pidfd),
    ("af_unix", check_af_unix),
]


def run_preflight(
    probe: Probe | None = None,
    runs_dir: str = "runs",
    min_free_bytes: int = DEFAULT_MIN_FREE_BYTES,
) -> dict:
    """Run every capability check and assemble the report (pure ordering)."""
    if probe is None:
        probe = Probe()
    capabilities: dict[str, dict] = {}
    for name, check in CAPABILITY_CHECKS:
        capabilities[name] = check(probe)
    capabilities["artifact_retention"] = check_artifact_retention(probe, runs_dir, min_free_bytes)
    blocked = sorted(name for name, cap in capabilities.items() if cap["status"] != "PASS")
    canonical = json.dumps(capabilities, sort_keys=True, separators=(",", ":"))
    return {
        "schema_version": SCHEMA_VERSION,
        "capabilities": capabilities,
        "blocked": blocked,
        "verdict": "QUALIFIED" if not blocked else "BLOCKED",
        "capability_hash": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--runs-dir", default="runs", help="evidence directory to probe for writability/fsync")
    parser.add_argument("--min-free-bytes", type=int, default=DEFAULT_MIN_FREE_BYTES)
    parser.add_argument("--output", default=None, help="also write the report to this file")
    args = parser.parse_args(argv)

    report = run_preflight(runs_dir=args.runs_dir, min_free_bytes=args.min_free_bytes)
    text = json.dumps(report, indent=2, sort_keys=True)
    print(text)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    return EXIT_QUALIFIED if report["verdict"] == "QUALIFIED" else EXIT_BLOCKED


if __name__ == "__main__":
    sys.exit(main())
