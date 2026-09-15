"""M4 host-side I/O and bounded *trusted-fixture* process supervision.

No helper in this module is an OS sandbox. Untrusted project verification is
blocked by the integrator. A hostile same-UID host process is outside this trust
boundary; the private worktree is never exposed to an untrusted running worker.
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


class M4SafetyError(WorkerContractError):
    pass


def artifact_parts(relative: str) -> tuple[str, ...]:
    if not isinstance(relative, str) or not relative or '\x00' in relative or '\\' in relative:
        raise M4SafetyError('invalid integration artifact path')
    path = PurePosixPath(relative)
    parts = path.parts
    if path.is_absolute() or not parts or path.as_posix() != relative:
        raise M4SafetyError('noncanonical integration artifact path')
    if any(p in {'.', '..'} or p.casefold() == '.git' for p in parts):
        raise M4SafetyError('reserved or traversing integration artifact path')
    return parts


def _directory_flags() -> int:
    if os.name != 'posix' or not hasattr(os, 'O_NOFOLLOW'):
        raise M4SafetyError('descriptor-relative no-follow I/O is required')
    return os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC


@contextmanager
def _parent(worktree: Path, relative: str, *, create: bool):
    parts = artifact_parts(relative)
    try:
        fd = os.open(worktree, _directory_flags())
    except OSError as exc:
        raise M4SafetyError('integration workspace root is unavailable') from exc
    try:
        for part in parts[:-1]:
            if create:
                try:
                    os.mkdir(part, 0o700, dir_fd=fd)
                except FileExistsError:
                    pass
            next_fd = os.open(part, _directory_flags(), dir_fd=fd)
            os.close(fd)
            fd = next_fd
        yield fd, parts[-1]
    finally:
        os.close(fd)


def _regular_entry(fd: int, name: str):
    try:
        info = os.stat(name, dir_fd=fd, follow_symlinks=False)
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise M4SafetyError('artifact must be a single-link regular file, not a link or directory')
    return info


def apply_artifact(worktree: Path, relative: str, data: bytes | None) -> None:
    """No target inode is opened for writing: replace a fresh private file.

    NOFOLLOW is used for each parent. A link substituted after validation is
    replaced/unlinked as a directory entry, never followed to external content.
    Existing hard links, symlinks (including dangling ones), and special files
    fail closed. Existing executable mode is preserved; new files are 0644.
    """
    try:
        with _parent(worktree, relative, create=data is not None) as (fd, name):
            previous = _regular_entry(fd, name)
            if data is None:
                if previous is not None:
                    os.unlink(name, dir_fd=fd)
                return
            temporary = '.residual-write-' + uuid.uuid4().hex
            out = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                          os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=fd)
            try:
                with os.fdopen(out, 'wb') as stream:
                    stream.write(data)
                    stream.flush()
                    os.fchmod(stream.fileno(), 0o755 if previous and previous.st_mode & 0o111 else 0o644)
                    os.fsync(stream.fileno())
                os.replace(temporary, name, src_dir_fd=fd, dst_dir_fd=fd)
                os.fsync(fd)
            finally:
                try:
                    os.unlink(temporary, dir_fd=fd)
                except FileNotFoundError:
                    pass
    except FileNotFoundError:
        if data is not None:
            raise M4SafetyError('integration parent vanished') from None
        # An absent parent proves that a deletion target is already absent.
    except OSError as exc:
        raise M4SafetyError('integration descriptor operation failed') from exc


def snapshot(worktree: Path) -> dict[str, tuple[str, int, str]]:
    """Read a bounded full inventory, including ignored files and .git marker.

    No Git status cache or clean filter participates. Hash file contents through
    no-follow descriptors, reject hard links/special files, and retain directory
    entries so even empty unreceipted directories are visible.
    """
    result: dict[str, tuple[str, int, str]] = {}
    total = 0

    def walk(fd: int, prefix: str = ''):
        nonlocal total
        for name in sorted(os.listdir(fd)):
            relative = prefix + name
            if len(result) >= 100_000:
                raise M4SafetyError('verification snapshot file-count limit exceeded')
            info = os.stat(name, dir_fd=fd, follow_symlinks=False)
            if stat.S_ISDIR(info.st_mode):
                child = os.open(name, _directory_flags(), dir_fd=fd)
                try:
                    result[relative] = ('directory', stat.S_IMODE(info.st_mode), '')
                    walk(child, relative + '/')
                finally:
                    os.close(child)
            elif stat.S_ISREG(info.st_mode) and info.st_nlink == 1:
                child = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK, dir_fd=fd)
                try:
                    before = os.fstat(child)
                    if (before.st_dev, before.st_ino) != (info.st_dev, info.st_ino) or before.st_nlink != 1:
                        raise M4SafetyError('snapshot identity changed')
                    if not stat.S_ISREG(before.st_mode):
                        raise M4SafetyError('snapshot target is not regular')
                    value = hashlib.sha256()
                    while True:
                        chunk = os.read(child, 65536)
                        if not chunk:
                            break
                        total += len(chunk)
                        if total > 1024 * 1024 * 1024:
                            raise M4SafetyError('verification snapshot byte limit exceeded')
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


# Deterministic parent-side wall-clock timeout marker, identical to the
# isolated lane's SANDBOX_TIMEOUT_EXIT: BOTH lanes return returncode 124 with
# timed_out=True for a typed timeout — one uniform contract (a real subprocess
# signal code after kill would leak the mechanism, not the outcome).
FIXTURE_TIMEOUT_EXIT = 124


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
        # Typed parent-side wall-clock timeout: deterministic returncode 124,
        # matching the isolated lane exactly (uniform timeout contract).
        return FixtureProcessResult('timeout', FIXTURE_TIMEOUT_EXIT, hashes[0].hexdigest(),
                                    hashes[1].hexdigest(), reason, timed_out=True)
    status = 'pass' if reason == 'exit' and process.returncode == 0 else 'fail'
    return FixtureProcessResult(status, process.returncode, hashes[0].hexdigest(),
                                hashes[1].hexdigest(), reason, timed_out=False)
