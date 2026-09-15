"""M4 safety: candidate workspaces are evidence, never trusted writes.

Artifact application writes bytes only for receipt-bound regular files, inside
the candidate worktree, with symlink/special-file rejection at every level.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import math
import os
from pathlib import Path, PurePosixPath
import selectors
import signal
import stat
import subprocess
import time
import uuid

from .worker_contract import WorkerContractError
from ._isolated_child import SANDBOX_TIMEOUT_EXIT


class M4SafetyError(WorkerContractError):
    pass


def artifact_parts(path: str) -> tuple[str, ...]:
    """Validate and split a receipt-declared artifact path (lexical policy)."""
    if not isinstance(path, str) or not path:
        raise M4SafetyError('invalid artifact path')
    if any(ch in path for ch in '\\:*?[]') or any(ord(ch) < 32 or ord(ch) == 127 for ch in path):
        raise M4SafetyError('invalid artifact path')
    pure = PurePosixPath(path)
    if pure.is_absolute() or any(part in {'', '.', '..'} for part in pure.parts):
        raise M4SafetyError('artifact path must be relative and normalized')
    if '.git' in (part.lower() for part in pure.parts):
        raise M4SafetyError('artifact path must not touch .git')
    return pure.parts


def _openat_dir(fd: int, name: str, *, create: bool) -> int:
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    if create:
        flags |= os.O_CREAT
        return os.open(name, flags, 0o700, dir_fd=fd)
    return os.open(name, flags, dir_fd=fd)


def _directory_flags() -> int:
    return os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC


def apply_artifact(worktree: Path, path: str, data: bytes | None) -> None:
    """Write or delete exactly one receipt-bound artifact inside ``worktree``.

    Every path component is opened with O_NOFOLLOW; the final write uses
    O_CREAT|O_EXCL for creation and an in-place truncate+write for an existing
    regular file owned by this worktree. ``data=None`` deletes the artifact.
    """
    parts = artifact_parts(path)
    root = os.open(str(worktree), _directory_flags())
    try:
        current = root
        for part in parts[:-1]:
            current = _openat_dir(current, part, create=True)
        name = parts[-1]
        if data is None:
            try:
                os.unlink(name, dir_fd=current)
            except FileNotFoundError:
                pass
            return
        flags = os.O_WRONLY | os.O_NOFOLLOW | os.O_CLOEXEC
        try:
            fd = os.open(name, flags, dir_fd=current)
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode):
                raise M4SafetyError('artifact target is not a regular file')
            os.ftruncate(fd, 0)
        except FileNotFoundError:
            fd = os.open(name, flags | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=current)
        try:
            view = memoryview(data)
            while view:
                written = os.write(fd, view)
                view = view[written:]
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        os.close(root)


def snapshot(worktree: Path) -> dict[str, tuple[str, int, str]]:
    """Hash every regular file under ``worktree``; reject links/specials."""
    result: dict[str, tuple[str, int, str]] = {}

    def walk(fd: int, prefix: str = '') -> None:
        for entry in os.listdir(fd):
            if entry in {'.', '..'}:
                continue
            info = os.stat(entry, dir_fd=fd, follow_symlinks=False)
            relative = f'{prefix}{entry}'
            if stat.S_ISDIR(info.st_mode):
                child_fd = os.open(entry, _directory_flags(), dir_fd=fd)
                try:
                    walk(child_fd, relative + '/')
                finally:
                    os.close(child_fd)
            elif stat.S_ISREG(info.st_mode):
                child = os.open(entry, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
                try:
                    before = os.fstat(child)
                    value = hashlib.sha256()
                    while True:
                        chunk = os.read(child, 65536)
                        if not chunk:
                            break
                        value.update(chunk)
                    after = os.fstat(child)
                    if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
                            after.st_size, after.st_mtime_ns, after.st_ctime_ns):
                        raise M4SafetyError('snapshot changed during read')
                    result[relative] = ('file', stat.S_IMODE(after.st_mode), value.hexdigest())
                finally:
                    os.close(child)
            else:
                raise M4SafetyError('snapshot contains a link or special file')

    try:
        fd = os.open(worktree, _directory_flags())
        try:
            walk(fd)
        finally:
            os.close(fd)
    except OSError as exc:
        raise M4SafetyError('cannot verify worktree inventory') from exc
    return result


@dataclass(frozen=True)
class FixtureProcessResult:
    status: str  # 'pass' | 'fail' | 'timeout' | 'unknown'
    returncode: int | None
    stdout_sha256: str
    stderr_sha256: str
    reason: str
    timed_out: bool = False


def run_trusted_fixture(argv: tuple[str, ...], worktree: Path, *,
                        timeout_s: float, output_limit: int) -> FixtureProcessResult:
    """Bound capture and kill the process group, including after leader exit.

    This is only for operator-authored, reviewed fixtures. It cannot contain a
    malicious program that changes session or accesses host files/network. The
    integrator must refuse this execution path without explicit fixture consent.
    """
    if type(timeout_s) not in (int, float) or not math.isfinite(timeout_s) or not 0 < timeout_s <= 900:
        raise M4SafetyError('invalid fixture deadline')
    if type(output_limit) is not int or not 1 <= output_limit <= 16 * 1024 * 1024:
        raise M4SafetyError('invalid fixture output limit')
    if not isinstance(argv, tuple) or not argv or not all(isinstance(a, str) and a and '\x00' not in a for a in argv):
        raise M4SafetyError('invalid fixture argv')
    if os.name != 'posix':
        raise M4SafetyError('trusted fixture supervisor requires POSIX process groups')
    env = {
        'PATH': os.environ.get('PATH', '/usr/bin:/bin'),
        'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8', 'PYTHONHASHSEED': '0',
        'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONNOUSERSITE': '1',
        'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': os.devnull,
        'GIT_NO_REPLACE_OBJECTS': '1',
    }
    hashes = [hashlib.sha256(), hashlib.sha256()]
    try:
        process = subprocess.Popen(argv, cwd=worktree, env=env, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   start_new_session=True, close_fds=True)
    except OSError:
        return FixtureProcessResult('unknown', None, hashes[0].hexdigest(), hashes[1].hexdigest(), 'launch_failed')
    deadline = time.monotonic() + timeout_s
    reason = 'exit'
    captured = 0
    try:
        with selectors.DefaultSelector() as selector:
            for index, stream in enumerate((process.stdout, process.stderr)):
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ, index)
            while selector.get_map() or process.poll() is None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    reason = 'timeout'
                    break
                for key, _ in selector.select(min(remaining, 0.05)):
                    chunk = os.read(key.fileobj.fileno(), 65536)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    permitted = max(0, output_limit - captured)
                    hashes[key.data].update(chunk[:permitted])
                    captured += len(chunk)
                    if captured > output_limit:
                        reason = 'output_limit'
                        break
                if reason != 'exit':
                    break
    finally:
        # Terminate leftover children even if the main command exited normally.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        for stream in (process.stdout, process.stderr):
            stream.close()
        process.wait(timeout=5)
    if reason == 'timeout':
        # Typed parent-side wall-clock timeout, matching the isolated lane:
        # the deterministic returncode is SANDBOX_TIMEOUT_EXIT (124) in BOTH
        # lanes — the child's killed signal returncode is discarded, since the
        # parent deadline break is the authoritative outcome here.
        return FixtureProcessResult('timeout', SANDBOX_TIMEOUT_EXIT,
                                    hashes[0].hexdigest(), hashes[1].hexdigest(),
                                    reason, timed_out=True)
    status = 'pass' if reason == 'exit' and process.returncode == 0 else 'fail'
    return FixtureProcessResult(status, process.returncode, hashes[0].hexdigest(),
                                hashes[1].hexdigest(), reason)
