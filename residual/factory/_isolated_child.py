"""Namespace bootstrap for the isolated M4 verification runner.

This module is executed as a *script* inside fresh Linux user/mount/PID/IPC/
UTS/network namespaces (via ``unshare --user --map-root-user --mount --pid
--fork --net --ipc --uts``).
It must stay stdlib-only and must never be imported on the host: importing the
package ``__init__`` would drag in unrelated factory machinery.

Protocol: the parent passes a JSON spec on stdin and a readiness pipe fd number
via the ``M4_SANDBOX_READY_FD`` environment variable. After the filesystem
namespace, chroot and resource limits are in place the child writes ``b"1"`` to
the readiness pipe and exec()s the verification command. Any setup failure
prints ``M4SANDBOX-ERROR: <detail>`` on stderr and exits 125 *without* exec, so
the parent can classify it as ERROR instead of a candidate FAIL.
"""
from __future__ import annotations

import ctypes
import json
import os
import resource
import sys

MS_RDONLY = 1
MS_BIND = 4096
MS_REC = 1 << 14
MS_PRIVATE = 1 << 18
MS_REMOUNT = 32

SANDBOX_ERROR_PREFIX = "M4SANDBOX-ERROR:"
SANDBOX_ERROR_EXIT = 125

_LIBC = ctypes.CDLL(None, use_errno=True)


def _mount(source: str | None, target: str, fstype: str | None, flags: int,
           data: str | None = None) -> None:
    rc = _LIBC.mount(
        source.encode() if source is not None else None,
        target.encode(),
        fstype.encode() if fstype is not None else None,
        ctypes.c_ulong(flags),
        data.encode() if data is not None else None,
    )
    if rc != 0:
        raise OSError(ctypes.get_errno(), f"mount {source!r} -> {target!r} failed")


def _fail(detail: str) -> "NoReturn":  # noqa: F821
    sys.stderr.write(f"{SANDBOX_ERROR_PREFIX} {detail}\n")
    sys.stderr.flush()
    os._exit(SANDBOX_ERROR_EXIT)


def main() -> None:
    try:
        spec = json.load(sys.stdin)
        argv = spec["argv"]
        worktree = spec["worktree"]
        newroot = spec["newroot"]
        memory_mb = int(spec["memory_mb"])
        cpu_s = int(spec["cpu_s"])
        ready_fd = int(os.environ["M4_SANDBOX_READY_FD"])
        if not isinstance(argv, list) or not argv or not all(
                isinstance(a, str) and a and "\x00" not in a for a in argv):
            raise ValueError("invalid argv")
        if not (os.path.isabs(worktree) and os.path.isdir(worktree)):
            raise ValueError("invalid worktree")
    except Exception as exc:
        _fail(f"spec: {exc}")

    try:
        # Detach from the host mount propagation before creating any mount.
        _mount(None, "/", None, MS_REC | MS_PRIVATE)

        # Minimal root: toolchain bind-mounted read-only, tmpfs scratch, the
        # candidate worktree bind-mounted read-only at its original absolute
        # path. Host $HOME, credentials, /etc and the source repository are
        # unreachable after chroot.
        os.makedirs(newroot, mode=0o700, exist_ok=True)
        _mount("tmpfs", newroot, "tmpfs", 0, "mode=700,size=256m")
        for name in ("usr", "bin", "lib", "lib64", "sbin"):
            source = "/" + name
            target = os.path.join(newroot, name)
            if os.path.islink(source):
                # Recreate merged-/usr symlinks (e.g. /lib64 -> usr/lib64);
                # the link target itself is covered by the /usr bind.
                os.symlink(os.readlink(source), target)
                continue
            if not os.path.isdir(source):
                continue
            os.makedirs(target, exist_ok=True)
            _mount(source, target, None, MS_BIND)
            _mount(source, target, None, MS_BIND | MS_REMOUNT | MS_RDONLY)
        tmp = os.path.join(newroot, "tmp")
        os.makedirs(tmp, exist_ok=True)
        _mount("tmpfs", tmp, "tmpfs", 0, "mode=1777,size=256m")
        target_wt = os.path.join(newroot, worktree.lstrip("/"))
        os.makedirs(target_wt, exist_ok=True)
        _mount(worktree, target_wt, None, MS_BIND)
        _mount(worktree, target_wt, None, MS_BIND | MS_REMOUNT | MS_RDONLY)
        dev = os.path.join(newroot, "dev")
        os.makedirs(dev, exist_ok=True)
        _mount("tmpfs", dev, "tmpfs", 0, "mode=755,size=16m")
        for node in ("null", "zero", "full", "urandom"):
            path = os.path.join(dev, node)
            fd = os.open(path, os.O_CREAT | os.O_WRONLY, 0o666)
            os.close(fd)
            _mount("/dev/" + node, path, None, MS_BIND)

        # Deterministic resource ceiling before candidate code runs.
        memory = memory_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (memory, memory))
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_s, cpu_s + 5))
        resource.setrlimit(resource.RLIMIT_NOFILE, (256, 256))
        resource.setrlimit(resource.RLIMIT_FSIZE, (64 * 1024 * 1024,) * 2)
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        try:
            resource.setrlimit(resource.RLIMIT_NPROC, (256, 256))
        except (ValueError, OSError):
            pass  # NPROC is advisory inside a private PID namespace.

        _LIBC.prctl(38, 1, 0, 0, 0)  # PR_SET_NO_NEW_PRIVS

        os.chroot(newroot)
        os.chdir(worktree)
    except Exception as exc:
        _fail(f"setup: {exc}")

    env = {
        "PATH": "/usr/bin:/bin",
        "TMPDIR": "/tmp",
        "HOME": "/tmp",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PYTHONHASHSEED": "0",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_NO_REPLACE_OBJECTS": "1",
    }
    try:
        os.write(ready_fd, b"1")
        os.close(ready_fd)
    except OSError as exc:
        _fail(f"ready pipe: {exc}")
    try:
        os.execvpe(argv[0], argv, env)
    except OSError as exc:
        _fail(f"exec {argv[0]!r}: {exc}")


if __name__ == "__main__":
    main()
