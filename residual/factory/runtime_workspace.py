"""Host-owned Git worktrees and descriptor-rooted brokered project I/O.

Workers never receive these descriptors or a checkout path. The local repository
and its Git configuration are operator-trusted; project file contents are not.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import stat
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .runtime_journal import private_directory
from .worker_contract import AttemptGuard, WorkerContract, WorkerContractError, _path

MAX_FILE_BYTES = 1024 * 1024


def git(repository: Path, *arguments: str, data: bytes | None = None,
        extra_env: dict[str, str] | None = None) -> bytes:
    env = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8",
           "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
           "GIT_TERMINAL_PROMPT": "0", "GIT_OPTIONAL_LOCKS": "0"}
    env.update(extra_env or {})
    command = ["git", "-c", f"core.hooksPath={os.devnull}", "-c", "core.fsmonitor=false",
               "-c", "submodule.recurse=false", "-c", "commit.gpgSign=false",
               "-C", str(repository), *arguments]
    result = subprocess.run(command, input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            timeout=20, env=env, check=False)
    if result.returncode:
        # Git diagnostics can contain private paths/configuration. Do not propagate them.
        raise WorkerContractError("managed Git operation failed")
    return result.stdout


@dataclass(frozen=True)
class CandidateTree:
    input_commit: str
    output_commit: str
    output_tree: str
    artifacts: tuple[tuple[str, str | None], ...]
    status: str = "UNTRUSTED_CANDIDATE"

    def to_dict(self) -> dict[str, Any]:
        return {"input_commit": self.input_commit, "output_commit": self.output_commit,
                "output_tree": self.output_tree, "artifacts": [list(x) for x in self.artifacts],
                "status": self.status}


class ManagedWorktree:
    """Each attempt owns one exact directory beneath a private runtime root."""
    def __init__(self, repository: str | Path, root: str | Path, contract: WorkerContract):
        self.repository = Path(repository).absolute()
        if self.repository.resolve() != self.repository or not self.repository.is_dir():
            raise WorkerContractError("repository must be a resolved local directory")
        self.root = private_directory(Path(root))
        if self.root == self.repository or self.repository.is_relative_to(self.root) or self.root.is_relative_to(self.repository):
            raise WorkerContractError("runtime storage and source repository must be disjoint")
        expected = self.root / contract.swarm_id / contract.attempt_id
        if Path(contract.workspace_root) != expected:
            raise WorkerContractError("workspace_root must equal runtime_root/swarm_id/attempt_id")
        self.path = expected
        self.objects = expected.parent / f".{contract.attempt_id}.objects"
        self.contract = contract
        self.created = False

    def create(self) -> None:
        if self.created or self.path.exists() or self.path.is_symlink():
            raise WorkerContractError("attempt workspace already exists")
        private_directory(self.path.parent)
        resolved = git(self.repository, "rev-parse", "--verify", f"{self.contract.input_commit}^{{commit}}").decode().strip()
        if resolved != self.contract.input_commit:
            raise WorkerContractError("input commit does not resolve exactly")
        git(self.repository, "worktree", "add", "--detach", str(self.path), resolved)
        self.created = True
        os.chmod(self.path, 0o700)

    def discard(self) -> None:
        if not self.created:
            return
        if self.path.resolve() != self.path or self.path != self.root / self.contract.swarm_id / self.contract.attempt_id:
            raise WorkerContractError("workspace identity changed; refusing destructive cleanup")
        git(self.repository, "worktree", "remove", "--force", str(self.path))
        self.created = False
        if self.objects.exists():
            if self.objects.is_symlink() or self.objects.resolve() != self.objects:
                raise WorkerContractError("quarantine object directory changed")
            shutil.rmtree(self.objects)

    def capture(self, broker: SafeFileBroker) -> CandidateTree:
        """Host creates a detached candidate commit, without hooks or clean filters.

        Nothing is merged or accepted. Only broker-touched files enter this index;
        pre-existing project files are inherited from the frozen input commit.
        """
        if not self.created:
            raise WorkerContractError("workspace is not active")
        index = self.path.parent / f".{self.contract.attempt_id}.candidate-index"
        if index.exists() or index.is_symlink():
            raise WorkerContractError("candidate index already exists")
        if self.objects.exists() or self.objects.is_symlink():
            raise WorkerContractError("quarantine objects already exist")
        private_directory(self.objects)
        source_objects = Path(git(self.path, "rev-parse", "--git-path", "objects").decode().strip())
        if not source_objects.is_absolute():
            source_objects = (self.path / source_objects).resolve()
        if ':' in str(source_objects):
            raise WorkerContractError("colon-containing Git object paths are unsupported")
        # Unreceipted objects stay outside the source repository's object store.
        env = {"GIT_INDEX_FILE": str(index), "GIT_OBJECT_DIRECTORY": str(self.objects),
               "GIT_ALTERNATE_OBJECT_DIRECTORIES": str(source_objects)}
        artifacts: list[tuple[str, str | None]] = []
        try:
            git(self.path, "read-tree", self.contract.input_commit, extra_env=env)
            for relative in sorted(broker.touched):
                value = broker.snapshot_output(relative)
                if value is None:
                    git(self.path, "update-index", "--force-remove", "--", relative, extra_env=env)
                    artifacts.append((relative, None))
                    continue
                data, executable = value
                blob = git(self.path, "hash-object", "-w", "--no-filters", "--stdin",
                           data=data, extra_env=env).decode().strip()
                mode = "100755" if executable else "100644"
                git(self.path, "update-index", "--add", "--cacheinfo", f"{mode},{blob},{relative}", extra_env=env)
                artifacts.append((relative, hashlib.sha256(data).hexdigest()))
            tree = git(self.path, "write-tree", extra_env=env).decode().strip()
            identity = {"GIT_AUTHOR_NAME": "Residual Factory", "GIT_AUTHOR_EMAIL": "factory@localhost",
                        "GIT_COMMITTER_NAME": "Residual Factory", "GIT_COMMITTER_EMAIL": "factory@localhost",
                        "GIT_AUTHOR_DATE": "2000-01-01T00:00:00Z", "GIT_COMMITTER_DATE": "2000-01-01T00:00:00Z"}
            commit = git(self.path, "commit-tree", tree, "-p", self.contract.input_commit,
                         data=f"Untrusted M2 candidate {self.contract.contract_hash}\n".encode(),
                         extra_env={**env, **identity}).decode().strip()
            return CandidateTree(self.contract.input_commit, commit, tree, tuple(artifacts))
        finally:
            index.unlink(missing_ok=True)
            Path(str(index) + '.lock').unlink(missing_ok=True)


class SafeFileBroker:
    """No symlink following, no hard links, bounded regular files, no ambient paths.

    O_NOFOLLOW and directory-relative opens enforce each component at lookup time.
    Workers cannot rename directories, create links or obtain host descriptors.
    """
    def __init__(self, worktree: ManagedWorktree, guard: AttemptGuard,
                 *, before_io: Callable[[], None] | None = None):
        self.worktree, self.guard = worktree, guard
        self._before_io = before_io or guard.check_deadline
        self._root = os.open(worktree.path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        self.touched: set[str] = set()
        self._lock = threading.Lock()

    def close(self) -> None:
        if self._root >= 0:
            os.close(self._root)
            self._root = -1

    def _parent(self, relative: str, *, create: bool = False) -> tuple[int, str]:
        _path(relative)
        components = relative.split('/')
        descriptor = os.dup(self._root)
        try:
            for part in components[:-1]:
                if create:
                    try:
                        os.mkdir(part, 0o700, dir_fd=descriptor)
                    except FileExistsError:
                        pass
                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                                dir_fd=descriptor)
                os.close(descriptor)
                descriptor = child
            return descriptor, components[-1]
        except BaseException:
            os.close(descriptor)
            raise

    @staticmethod
    def _regular(descriptor: int) -> os.stat_result:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise WorkerContractError("only singly-linked regular files are supported")
        if info.st_size > MAX_FILE_BYTES:
            raise WorkerContractError("project file exceeds runtime byte limit")
        return info

    def _read(self, relative: str) -> tuple[bytes, bool]:
        parent, leaf = self._parent(relative)
        try:
            fd = os.open(leaf, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=parent)
            try:
                info = self._regular(fd)
                with os.fdopen(fd, 'rb', closefd=False) as stream:
                    content = stream.read(MAX_FILE_BYTES + 1)
                if len(content) > MAX_FILE_BYTES:
                    raise WorkerContractError("file grew beyond byte limit")
                return content, bool(info.st_mode & 0o111)
            finally:
                os.close(fd)
        finally:
            os.close(parent)

    def _write(self, relative: str, data: bytes) -> None:
        parent, leaf = self._parent(relative, create=True)
        try:
            # Do not truncate until type/link checks pass. No worker can race us;
            # intermediate directories and final files are never followed as links.
            fd = os.open(leaf, os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
                         0o600, dir_fd=parent)
            try:
                self._regular(fd)
                os.ftruncate(fd, 0)
                view = memoryview(data)
                while view:
                    count = os.write(fd, view)
                    view = view[count:]
                os.fsync(fd)
            finally:
                os.close(fd)
            os.fsync(parent)
        finally:
            os.close(parent)
        self.touched.add(relative)

    def _delete(self, relative: str) -> None:
        parent, leaf = self._parent(relative)
        try:
            fd = os.open(leaf, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=parent)
            try:
                self._regular(fd)
            finally:
                os.close(fd)
            os.unlink(leaf, dir_fd=parent)
            os.fsync(parent)
        finally:
            os.close(parent)
        self.touched.add(relative)

    def dispatch(self, operation: str, arguments: dict[str, Any]) -> Any:
        with self._lock:
            self.guard.authorize_tool(operation)
            required = {'path', 'content'} if operation == 'write_file' else {'path'}
            if operation not in {'read_file', 'write_file', 'delete_file'} or set(arguments) != required:
                self.guard.fail('tool', 'broker_protocol', {'operation': operation, 'reason': 'unsupported_shape'})
            relative = arguments['path']
            write = operation != 'read_file'
            self.guard.authorize_path(relative, write=write)
            # Recheck after synchronous observation acknowledgement: the watchdog
            # may have fenced this attempt while its audit writer was blocked.
            self._before_io()
            try:
                if operation == 'read_file':
                    return self._read(relative)[0].decode('utf-8')
                if operation == 'write_file':
                    content = arguments['content']
                    if not isinstance(content, str):
                        raise WorkerContractError('write content must be text')
                    data = content.encode('utf-8')
                    if len(data) > MAX_FILE_BYTES:
                        raise WorkerContractError('write exceeds runtime byte limit')
                    self._write(relative, data)
                else:
                    self._delete(relative)
                return None
            except (OSError, ValueError, TypeError) as exc:
                self.guard.fail('filesystem', 'broker_file_boundary',
                                {'path': str(relative)[:1024], 'operation': operation,
                                 'reason': type(exc).__name__})

    def snapshot_output(self, relative: str) -> tuple[bytes, bool] | None:
        if relative not in self.touched or not self.guard.contract.permits_path(relative, write=True):
            raise WorkerContractError('not a declared output')
        try:
            return self._read(relative)
        except FileNotFoundError:
            return None
