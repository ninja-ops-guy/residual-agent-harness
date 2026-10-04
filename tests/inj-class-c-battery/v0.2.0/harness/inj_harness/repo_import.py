"""Live import of the pinned v1 system-prompt bytes (never copied).

The harness-faithful mode binds its claim to the EXACT prompt bytes the v1
harness uses at runtime. Those bytes live in residual/station/service.py in
the repo; this module imports them live from a repo checkout resolved via
--repo / RESIDUAL_REPO (default ~/workspace/residual-agent-harness), added
to sys.path. If the import fails, the caller aborts with a clear error —
there is no fallback prompt text, so a stale or missing repo can never
silently produce a receipt against wrong bytes.
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys

ENV_VAR = "RESIDUAL_REPO"
DEFAULT_REPO = os.path.expanduser("~/workspace/residual-agent-harness")
SOURCE_FILE = "residual/station/service.py"
EXPECTED_COMMIT = "ed271eeea9407b3df3919579f492cdf1a0f46849"
EXPECTED_COMMIT_SHORT = "ed271eee"


class RepoImportError(RuntimeError):
    """Raised when the v1 repo cannot be resolved or the prompt bytes imported."""


def resolve_repo(explicit: str | None = None) -> str:
    """Resolve the repo path: --repo > RESIDUAL_REPO env > default."""
    path = explicit or os.environ.get(ENV_VAR) or DEFAULT_REPO
    path = os.path.expanduser(path)
    if not os.path.isdir(path):
        raise RepoImportError(
            f"repo path is not a directory: {path!r} "
            f"(set --repo or {ENV_VAR}; default {DEFAULT_REPO!r})"
        )
    return path


def _git_head(repo: str) -> str:
    """Full commit SHA of the repo checkout, or an honest unknown marker."""
    try:
        out = subprocess.run(
            ["git", "-C", repo, "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=15, check=False,
        )
    except Exception:
        return "unknown (git unavailable)"
    sha = (out.stdout or "").strip()
    if out.returncode != 0 or len(sha) != 40:
        return "unknown (not a git checkout or rev-parse failed)"
    return sha


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def import_prompt_bytes(repo: str | None = None) -> dict:
    """Import RUNNER_SYSTEM / REVIEW_SYSTEM live from the repo.

    Returns a provenance dict: repo path, the two prompt strings, their
    sha256 hashes, and the checkout's commit SHA. Raises RepoImportError
    (never returns partial data) on any failure.
    """
    repo_path = resolve_repo(repo)
    if repo_path not in sys.path:
        sys.path.insert(0, repo_path)
    try:
        from residual.station import service
    except Exception as exc:
        raise RepoImportError(
            f"failed to import residual.station.service from repo "
            f"{repo_path!r}: {type(exc).__name__}: {exc}"
        ) from exc
    try:
        runner = service.RUNNER_SYSTEM
        review = service.REVIEW_SYSTEM
    except AttributeError as exc:
        raise RepoImportError(
            f"residual.station.service in {repo_path!r} does not define the "
            f"pinned prompt constants: {exc}"
        ) from exc
    if not isinstance(runner, str) or not runner:
        raise RepoImportError("RUNNER_SYSTEM import is empty or not a string")
    if not isinstance(review, str) or not review:
        raise RepoImportError("REVIEW_SYSTEM import is empty or not a string")
    commit = _git_head(repo_path)
    return {
        "repo": repo_path,
        "source_file": SOURCE_FILE,
        "runner_system": runner,
        "review_system": review,
        "prompt_sha256": {
            "RUNNER_SYSTEM": sha256_hex(runner),
            "REVIEW_SYSTEM": sha256_hex(review),
        },
        "source_commit": commit,
        "expected_commit": EXPECTED_COMMIT,
        "commit_matches_expected": commit == EXPECTED_COMMIT,
    }
