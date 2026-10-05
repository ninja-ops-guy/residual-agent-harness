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
EXPECTED_COMMIT = "ca6cd2e98ee7d7293e88e97ebfd304da06a61076"
EXPECTED_COMMIT_SHORT = "ca6cd2e"


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


def _module_origin_ok(module, repo_path: str) -> tuple:
    """Check the imported module's __file__ belongs to the selected checkout.

    Returns (ok: bool, real_file: str|None). A previously cached module from
    another tree must never silently supply prompt bytes while the receipt
    records the selected tree's commit.
    """
    mod_file = getattr(module, "__file__", None)
    if not mod_file:
        return False, None
    real_mod = os.path.realpath(mod_file)
    real_repo = os.path.realpath(repo_path)
    return real_mod.startswith(real_repo + os.sep), real_mod


def _evict_residual_modules() -> None:
    """Remove cached residual* modules so a reimport resolves fresh."""
    for name in [n for n in sys.modules if n == "residual" or n.startswith("residual.")]:
        del sys.modules[name]


def _import_from_repo(repo_path: str, dotted: str):
    """Import a dotted module from the selected repo with origin verification.

    On an origin mismatch (cached module from another tree), evicts cached
    residual modules, re-prepends the repo, reimports once, and re-verifies.
    Raises RepoImportError if the final module still does not belong to the
    selected checkout.
    """
    if repo_path not in sys.path:
        sys.path.insert(0, repo_path)
    try:
        module = __import__(dotted, fromlist=["*"])
    except Exception as exc:
        raise RepoImportError(
            f"failed to import {dotted} from repo {repo_path!r}: "
            f"{type(exc).__name__}: {exc}"
        ) from exc
    ok, mod_file = _module_origin_ok(module, repo_path)
    if not ok:
        # Recovery attempt: evict stale cache, force repo precedence, reimport.
        _evict_residual_modules()
        if repo_path in sys.path:
            sys.path.remove(repo_path)
        sys.path.insert(0, repo_path)
        try:
            module = __import__(dotted, fromlist=["*"])
        except Exception as exc:
            raise RepoImportError(
                f"failed to reimport {dotted} from repo {repo_path!r} after "
                f"cache eviction: {type(exc).__name__}: {exc}"
            ) from exc
        ok, mod_file = _module_origin_ok(module, repo_path)
    if not ok:
        raise RepoImportError(
            f"{dotted} resolves to {mod_file!r}, outside the selected repo "
            f"{repo_path!r} — refusing to bind prompt bytes from another tree. "
            f"Clear sys.modules or fix --repo/{ENV_VAR}."
        )
    return module, mod_file


def import_prompt_bytes(repo: str | None = None) -> dict:
    """Import RUNNER_SYSTEM / REVIEW_SYSTEM live from the repo.

    Returns a provenance dict: repo path, the two prompt strings, their
    sha256 hashes, the checkout's commit SHA, the actual module file the
    bytes were imported from, and the module-origin verification result.
    Raises RepoImportError (never returns partial data) on any failure.
    """
    repo_path = resolve_repo(repo)
    service, mod_file = _import_from_repo(repo_path, "residual.station.service")
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
        "prompt_source_file": mod_file,
        "module_origin_verified": True,
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


def import_canonical(repo: str | None = None):
    """Import residual.core.canonical live, with the same origin discipline.

    Returns (canonical_fn, provenance: dict). The harness-faithful mode
    serializes evidence packets with the repo's actual canonical(), so the
    function must come from the selected checkout — verified, not assumed.
    """
    repo_path = resolve_repo(repo)
    core_mod, mod_file = _import_from_repo(repo_path, "residual.core")
    fn = getattr(core_mod, "canonical", None)
    if not callable(fn):
        raise RepoImportError(
            f"residual.core in {repo_path!r} has no callable canonical()"
        )
    return fn, {
        "canonical_source_file": mod_file,
        "module_origin_verified": True,
    }
