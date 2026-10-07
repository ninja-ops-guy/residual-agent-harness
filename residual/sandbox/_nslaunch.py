"""Namespace launcher: mini-bwrap using user/mount/pid/net namespaces.

Invoked as ``python -m residual.sandbox._nslaunch -- argv...`` with a JSON
config in ``SANDBOX_LAUNCH_CONFIG``::

    {"deny_net": bool, "read": [paths], "write": [paths],
     "workdir": "/path", "runtime": bool}

Requirement IDs (track B):
  B-R14: The launcher MUST unshare user+mount namespaces, bind-mount only
         the allowlisted paths (plus a minimal runtime root when
         ``runtime`` is true) into a fresh tmpfs root, chroot into it, and
         MUST drop all environment variables not passed through the spec.
  B-R15: With ``deny_net`` the launcher MUST unshare the network namespace;
         sandboxed code then has no route and no external sockets.
  B-R16: The launcher MUST unshare the PID namespace and act as a reaping
         subreaper parent so a fork bomb dies with the sandbox.
"""
from __future__ import annotations

import ctypes
import ctypes.util
import json
import os
import signal
import sys

CLONE_NEWUSER = 0x10000000
CLONE_NEWNS = 0x00020000
CLONE_NEWPID = 0x20000000
CLONE_NEWNET = 0x40000000
MS_BIND = 4096
MS_REC = 16384
MS_RDONLY = 1
MS_REMOUNT = 32
MNT_DETACH = 2
PR_SET_PDEATHSIG = 1

_LIBC = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)

# Minimal runtime so dynamically linked binaries work in the chroot.
_RUNTIME_DIRS = ("/usr", "/lib", "/lib64", "/bin", "/sbin")
_RUNTIME_FILES = ("/etc/ld.so.cache",)
_DEV_FILES = ("/dev/null", "/dev/zero", "/dev/urandom")


def _mount(src: str, dst: str, fstype: str | None, flags: int, data: str = "") -> None:
    if _LIBC.mount(src.encode() if src else None, dst.encode(),
                   fstype.encode() if fstype else None, flags,
                   data.encode() if data else None) != 0:
        err = ctypes.get_errno()
        raise OSError(err, f"mount {src} -> {dst} failed: {os.strerror(err)}")


def _write_file(path: str, text: str) -> None:
    with open(path, "w") as fh:
        fh.write(text)


def _bind(src: str, dst: str, *, readonly: bool) -> None:
    if os.path.isdir(src):
        os.makedirs(dst, exist_ok=True)
    else:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, "a").close()
    _mount(src, dst, None, MS_BIND | MS_REC)
    if readonly:
        _mount(src, dst, None, MS_BIND | MS_REMOUNT | MS_RDONLY | MS_REC)


def _enter_namespaces(deny_net: bool) -> None:
    flags = CLONE_NEWUSER | CLONE_NEWNS | CLONE_NEWPID
    if deny_net:
        flags |= CLONE_NEWNET
    uid, gid = os.getuid(), os.getgid()  # capture BEFORE unshare (post-unshare is nobody)
    if _LIBC.unshare(flags) != 0:
        err = ctypes.get_errno()
        raise OSError(err, f"unshare failed: {os.strerror(err)}")
    _write_file("/proc/self/setgroups", "deny")
    _write_file("/proc/self/uid_map", f"0 {uid} 1")
    _write_file("/proc/self/gid_map", f"0 {gid} 1")
    # No host mounts may propagate into the jail.
    _mount("none", "/", None, MS_REC | (1 << 18), "")  # MS_PRIVATE


def _build_root(cfg: dict) -> str:
    root = "/tmp/.sandbox-root"
    os.makedirs(root, exist_ok=True)
    _mount("tmpfs", root, "tmpfs", 0, "size=16m")
    # /tmp must exist BEFORE any allowlist bind beneath it, else the tmpfs
    # would shadow the bind.
    os.makedirs(root + "/tmp", exist_ok=True)
    _mount("tmpfs", root + "/tmp", "tmpfs", 0, "size=32m")
    mounted: set[str] = set()

    def add(src: str, readonly: bool) -> None:
        # Bind at the literal path: /bin may be a symlink to /usr/bin, and the
        # mount syscall resolves the source, preserving the jail's layout.
        src = src.rstrip("/") or "/"
        key = os.path.realpath(src)
        if key in mounted or not os.path.exists(src):
            return
        mounted.add(key)
        try:
            _bind(src, root + src, readonly=readonly)
        except OSError:
            pass  # optional runtime piece missing; payload will fail loudly

    if cfg.get("runtime"):
        for d in _RUNTIME_DIRS:
            add(d, readonly=True)
        for f in _RUNTIME_FILES:
            add(f, readonly=True)
        for f in _DEV_FILES:
            add(f, readonly=True)
        # No synthetic /etc/passwd or /etc/group: a fake host-style account
        # database would let sandboxed code read a canonical sensitive path
        # outside the allowlist and would mask real containment checks. The
        # runtime payload does not need account resolution; the jail's /etc
        # only ever carries the loader cache bind above.
    for path in cfg.get("read", []):
        add(path, readonly=True)
    for path in cfg.get("write", []):
        add(path, readonly=False)
    # The jail root itself MUST be read-only; only explicit write binds and
    # /tmp are writable (B-R2, deny-by-default).
    _mount("", root, "", MS_REMOUNT | MS_RDONLY)
    return root


def _child(cfg: dict, argv: list[str]) -> None:  # PID 1 of the new pid ns
    _LIBC.prctl(PR_SET_PDEATHSIG, signal.SIGKILL)
    import resource
    max_pids = int(cfg.get("max_pids") or 0)
    if max_pids > 0:
        # RLIMIT_NPROC charges every task of the real UID host-wide
        # (threads included); budget = measured task base + limit.
        budget = int(cfg.get("nproc_base") or 0) + max_pids
        resource.setrlimit(resource.RLIMIT_NPROC, (budget, budget))
    memory_mb = int(cfg.get("memory_mb") or 0)
    if memory_mb > 0:
        mem = memory_mb << 20
        resource.setrlimit(resource.RLIMIT_AS, (mem, mem))
    root = _build_root(cfg)
    os.chroot(root)
    workdir = cfg.get("workdir") or "/"
    os.chdir(workdir if os.path.isdir(workdir) else "/")
    env = {"PATH": "/usr/bin:/bin", "HOME": "/tmp"}
    try:
        os.execvpe(argv[0], argv, env)
    except OSError as exc:
        sys.stderr.write(f"sandbox-exec: {exc}\n")
        os._exit(127)


def main() -> None:
    args = sys.argv[1:]
    probe = "--probe" in args
    if "--" in args:
        argv = args[args.index("--") + 1:]
    else:
        argv = []
    cfg = json.loads(os.environ.get("SANDBOX_LAUNCH_CONFIG", "{}"))
    try:
        _enter_namespaces(bool(cfg.get("deny_net", True)))
    except OSError as exc:
        sys.stderr.write(f"nslaunch: {exc}\n")
        sys.exit(125)
    if probe:
        sys.exit(0)
    if not argv:
        sys.stderr.write("nslaunch: no command\n")
        sys.exit(125)
    # PID namespace requires a fork: the child becomes PID 1 inside.
    pid = os.fork()
    if pid == 0:
        try:
            _child(cfg, argv)
        except BaseException as exc:  # containment: report, never propagate
            sys.stderr.write(f"nslaunch-child: {exc}\n")
            os._exit(126)
    # Parent: reap everything so a fork bomb cannot strand zombies.
    status = 0
    while True:
        try:
            done, st = os.wait()
        except ChildProcessError:
            break
        if done == pid:
            status = st
    if os.WIFEXITED(status):
        sys.exit(os.WEXITSTATUS(status))
    if os.WIFSIGNALED(status):
        os.kill(os.getpid(), os.WTERMSIG(status))
    sys.exit(126)


if __name__ == "__main__":
    main()
