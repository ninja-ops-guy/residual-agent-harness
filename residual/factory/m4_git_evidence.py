"""Typed Git base-evidence reads for M4 integration.

A base-revision blob lookup has four honest outcomes:

* ``PRESENT`` — the commit was validated and the exact literal path exists as a
  regular blob whose bytes match its object identity;
* ``ABSENT`` — the commit was validated and a successful exact-path ``ls-tree``
  proved the path does not exist;
* ``UNKNOWN`` — the base itself cannot be validated (unresolvable/incomparable
  commit, Git timeout), so nothing is known about the path;
* ``ERROR`` — the repository or object store is broken (command failure,
  corrupt object, ambiguous entry, unexpected entry type).

A failed lookup is never silently mapped to ABSENT. Callers must fail closed on
UNKNOWN/ERROR.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import os
from pathlib import Path
import re
import subprocess

from .m4_safety import artifact_parts

MAX_BASE_BLOB_BYTES = 16 * 1024 * 1024

_COMMIT_RE = re.compile(r"[0-9a-f]{40}")


class GitEvidenceState(str, Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    UNKNOWN = "UNKNOWN"
    ERROR = "ERROR"


@dataclass(frozen=True)
class GitBlobEvidence:
    state: GitEvidenceState
    data: bytes | None
    detail: str

    def __post_init__(self) -> None:
        if self.state is GitEvidenceState.PRESENT and self.data is None:
            raise ValueError("PRESENT evidence requires bytes")
        if self.state in (GitEvidenceState.ABSENT, GitEvidenceState.UNKNOWN,
                          GitEvidenceState.ERROR) and self.data is not None:
            raise ValueError("only PRESENT evidence carries bytes")


def _run(repository: Path, arguments: list[str], *, data: bytes | None = None) -> tuple[int, bytes]:
    env = {
        "PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8",
        "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_TERMINAL_PROMPT": "0", "GIT_OPTIONAL_LOCKS": "0",
        "GIT_NO_REPLACE_OBJECTS": "1",
    }
    command = [
        "git", "-c", f"core.hooksPath={os.devnull}", "-c", "core.fsmonitor=false",
        "-c", "submodule.recurse=false", "-c", "commit.gpgSign=false",
        "-C", str(repository), *arguments,
    ]
    try:
        result = subprocess.run(command, input=data, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, timeout=20, check=False, env=env)
    except subprocess.TimeoutExpired:
        raise _GitTimeout("git command timed out")
    except OSError:
        raise _GitCommandFailure("git command could not start")
    return result.returncode, result.stdout


class _GitTimeout(Exception):
    pass


class _GitCommandFailure(Exception):
    pass


def read_base_blob(repository: str | Path, commit: str, path: str) -> GitBlobEvidence:
    """Read ``path`` from validated base ``commit`` with honest outcome typing."""
    repository = Path(repository)
    try:
        parts = artifact_parts(path)
    except Exception:
        return GitBlobEvidence(GitEvidenceState.ERROR, None, "invalid_path")
    del parts
    if not isinstance(commit, str) or _COMMIT_RE.fullmatch(commit) is None:
        return GitBlobEvidence(GitEvidenceState.ERROR, None, "invalid_commit_ref")
    try:
        rc, resolved = _run(repository, ["rev-parse", "--verify", f"{commit}^{{commit}}"])
    except _GitTimeout:
        return GitBlobEvidence(GitEvidenceState.UNKNOWN, None, "git_timeout")
    except _GitCommandFailure:
        return GitBlobEvidence(GitEvidenceState.ERROR, None, "git_command_failed")
    if rc != 0 or resolved.decode("ascii", "replace").strip() != commit:
        # The base cannot be validated; nothing can be concluded about the path.
        return GitBlobEvidence(GitEvidenceState.UNKNOWN, None, "base_commit_unresolvable")
    try:
        rc, listing = _run(repository, ["ls-tree", "-z", "--full-tree", commit,
                                        "--", f":(literal){path}"])
    except _GitTimeout:
        return GitBlobEvidence(GitEvidenceState.UNKNOWN, None, "git_timeout")
    except _GitCommandFailure:
        return GitBlobEvidence(GitEvidenceState.ERROR, None, "git_command_failed")
    if rc != 0:
        return GitBlobEvidence(GitEvidenceState.ERROR, None, "git_command_failed")
    if not listing:
        # A successful exact-path lookup against a validated commit proves absence.
        return GitBlobEvidence(GitEvidenceState.ABSENT, None, "path_not_in_base_tree")
    entries = listing.rstrip(b"\0").split(b"\0")
    if len(entries) != 1:
        return GitBlobEvidence(GitEvidenceState.ERROR, None, "ambiguous_base_path")
    try:
        metadata, name = entries[0].split(b"\t", 1)
        mode, kind, oid = metadata.split()
        if name != path.encode("utf-8") or kind != b"blob" or mode not in (b"100644", b"100755"):
            return GitBlobEvidence(GitEvidenceState.ERROR, None, "base_entry_not_regular_blob")
        object_id = oid.decode("ascii")
    except (ValueError, UnicodeDecodeError):
        return GitBlobEvidence(GitEvidenceState.ERROR, None, "malformed_ls_tree_entry")
    try:
        rc, size_raw = _run(repository, ["cat-file", "-s", object_id])
        if rc != 0:
            return GitBlobEvidence(GitEvidenceState.ERROR, None, "object_unreadable")
        size = int(size_raw)
        if size > MAX_BASE_BLOB_BYTES:
            return GitBlobEvidence(GitEvidenceState.ERROR, None, "base_blob_too_large")
        rc, data = _run(repository, ["cat-file", "blob", object_id])
        if rc != 0:
            return GitBlobEvidence(GitEvidenceState.ERROR, None, "object_unreadable")
        rc, actual = _run(repository, ["hash-object", "--no-filters", "--stdin"], data=data)
        if rc != 0 or len(data) != size or actual.strip().decode("ascii", "replace") != object_id:
            return GitBlobEvidence(GitEvidenceState.ERROR, None, "object_bytes_mismatch_identity")
    except _GitTimeout:
        return GitBlobEvidence(GitEvidenceState.UNKNOWN, None, "git_timeout")
    except _GitCommandFailure:
        return GitBlobEvidence(GitEvidenceState.ERROR, None, "git_command_failed")
    return GitBlobEvidence(GitEvidenceState.PRESENT, data, "ok")
