"""Administrator-owned resource catalog for Copilot Firmware missions."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from ...core import ContractError, digest, identifier
from ...factory.runtime_workspace import WorkerContractError, git

_HEX_COMMIT = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")


def _context_path(value: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 512:
        raise ContractError("repository context path is invalid")
    if value.startswith("/") or "\\" in value or ":" in value:
        raise ContractError("repository context path must be relative POSIX")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise ContractError("repository context path contains control characters")
    path = PurePosixPath(value)
    if str(path) != value or any(part in {"", ".", ".."} for part in path.parts):
        raise ContractError("repository context path must be normalized")
    if any(part.lower() == ".git" for part in path.parts):
        raise ContractError("repository metadata cannot be context")
    return value


@dataclass(frozen=True)
class RepositorySnapshot:
    repository_id: str
    commit: str
    contents: tuple[tuple[str, str], ...]
    file_hashes: tuple[tuple[str, str], ...]
    snapshot_hash: str

    def __post_init__(self):
        identifier(self.repository_id)
        if not isinstance(self.commit, str) or not _HEX_COMMIT.fullmatch(self.commit):
            raise ContractError("repository snapshot commit is invalid")
        if not self.contents:
            raise ContractError("repository snapshot requires context")
        if tuple(path for path, _ in self.contents) != tuple(
            path for path, _ in self.file_hashes
        ):
            raise ContractError("repository snapshot file/hash order mismatch")

    def context(self) -> dict[str, str]:
        return dict(self.contents)


@dataclass(frozen=True)
class RepositoryResource:
    """Trusted mapping from an opaque repository_id to a local managed Git repo."""

    repository_id: str
    root: Path
    context_paths: tuple[str, ...]
    max_file_bytes: int = 64 * 1024
    max_total_bytes: int = 256 * 1024

    def __post_init__(self):
        identifier(self.repository_id)
        root = Path(self.root).absolute()
        if not root.is_dir() or root.resolve() != root:
            raise ContractError("repository resource must be a resolved local directory")
        if (
            not isinstance(self.context_paths, tuple)
            or not self.context_paths
            or len(self.context_paths) > 128
        ):
            raise ContractError("repository resource requires bounded context paths")
        normalized = tuple(sorted(_context_path(p) for p in self.context_paths))
        if len(set(normalized)) != len(normalized):
            raise ContractError("duplicate repository context path")
        if (
            type(self.max_file_bytes) is not int
            or not 1 <= self.max_file_bytes <= 1024 * 1024
            or type(self.max_total_bytes) is not int
            or not self.max_file_bytes <= self.max_total_bytes <= 4 * 1024 * 1024
        ):
            raise ContractError("repository context byte limits are invalid")
        try:
            inside = git(root, "rev-parse", "--is-inside-work-tree").decode().strip()
        except WorkerContractError as exc:
            raise ContractError("repository resource is not a usable Git repository") from exc
        if inside != "true":
            raise ContractError("repository resource is not a Git work tree")
        object.__setattr__(self, "root", root)
        object.__setattr__(self, "context_paths", normalized)

    def snapshot(self) -> RepositorySnapshot:
        try:
            commit = git(self.root, "rev-parse", "--verify", "HEAD^{commit}").decode().strip()
        except WorkerContractError as exc:
            raise ContractError("repository HEAD cannot be resolved") from exc
        if not _HEX_COMMIT.fullmatch(commit):
            raise ContractError("repository returned a non-full commit id")

        contents: list[tuple[str, str]] = []
        hashes: list[tuple[str, str]] = []
        total = 0
        for path in self.context_paths:
            try:
                tree = git(self.root, "ls-tree", commit, "--", path).decode("utf-8")
                if not tree.strip():
                    raise ContractError("configured repository context path is missing")
                mode = tree.split(None, 1)[0]
                if mode not in {"100644", "100755"}:
                    raise ContractError("repository context must be a regular file")
                raw_size = git(self.root, "cat-file", "-s", f"{commit}:{path}").decode().strip()
                size = int(raw_size)
                if size < 0 or size > self.max_file_bytes:
                    raise ContractError("repository context file exceeds configured limit")
                total += size
                if total > self.max_total_bytes:
                    raise ContractError("repository context exceeds configured total limit")
                raw = git(self.root, "show", f"{commit}:{path}")
            except (WorkerContractError, ValueError) as exc:
                raise ContractError("configured repository context cannot be read") from exc
            if len(raw) != size:
                raise ContractError("repository context size changed during snapshot")
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ContractError("repository context must be UTF-8 text") from exc
            contents.append((path, text))
            hashes.append((path, digest({"bytes_sha256": __import__("hashlib").sha256(raw).hexdigest()})))

        snapshot_hash = digest({
            "repository_id": self.repository_id,
            "commit": commit,
            "files": [{"path": p, "hash": h} for p, h in hashes],
        })
        return RepositorySnapshot(
            repository_id=self.repository_id,
            commit=commit,
            contents=tuple(contents),
            file_hashes=tuple(hashes),
            snapshot_hash=snapshot_hash,
        )


class RepositoryCatalog:
    """Immutable-at-construction set of administrator-approved repositories."""

    def __init__(self, resources: tuple[RepositoryResource, ...]):
        if not isinstance(resources, tuple) or not resources:
            raise ContractError("repository catalog requires resources")
        table: dict[str, RepositoryResource] = {}
        for resource in resources:
            if not isinstance(resource, RepositoryResource):
                raise ContractError("repository catalog entries must be RepositoryResource")
            if resource.repository_id in table:
                raise ContractError("duplicate repository_id in catalog")
            table[resource.repository_id] = resource
        self._resources = table

    def resolve(self, repository_id: str) -> RepositoryResource:
        identifier(repository_id)
        resource = self._resources.get(repository_id)
        if resource is None:
            raise ContractError("repository_id is not configured for this deployment")
        return resource

    def snapshot(self, repository_id: str) -> RepositorySnapshot:
        return self.resolve(repository_id).snapshot()

    @property
    def repository_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._resources))
