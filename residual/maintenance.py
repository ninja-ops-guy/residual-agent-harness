"""Read-only diagnostics and bounded self-update support for RESIDUAL."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from urllib.parse import unquote, urlparse

from .core import ContractError
from .version import current_version

PACKAGE = "residual-agent-harness"
REPOSITORY = "https://github.com/ninja-ops-guy/residual-agent-harness.git"
DEFAULT_BRANCH = "main"


@dataclass(frozen=True)
class Installation:
    method: str
    package_path: str
    repo_path: str | None
    editable: bool


def _run(argv: list[str], *, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            argv,
            cwd=str(cwd) if cwd else None,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=check,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = ""
        if isinstance(exc, subprocess.CalledProcessError):
            detail = (exc.stderr or exc.stdout or "").strip()
        raise ContractError(f"maintenance command failed: {detail[:240] or argv[0]}") from None


def _repo_from_path(path: Path) -> Path | None:
    current = path.resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists() and (candidate / "pyproject.toml").exists():
            return candidate
    return None


def _direct_url() -> dict:
    try:
        dist = metadata.distribution(PACKAGE)
        raw = dist.read_text("direct_url.json")
    except metadata.PackageNotFoundError:
        return {}
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def inspect_installation() -> Installation:
    package_path = Path(__file__).resolve().parent
    direct = _direct_url()
    editable = bool((direct.get("dir_info") or {}).get("editable"))
    repo = None

    url = direct.get("url")
    if isinstance(url, str) and url.startswith("file:"):
        parsed = urlparse(url)
        local = Path(unquote(parsed.path))
        if os.name == "nt" and parsed.netloc:
            local = Path(f"//{parsed.netloc}{unquote(parsed.path)}")
        repo = _repo_from_path(local)

    repo = repo or _repo_from_path(package_path)
    if editable:
        method = "editable"
    elif repo is not None:
        method = "source-checkout"
    else:
        method = "package"

    return Installation(method, str(package_path), str(repo) if repo else None, editable)


def _git(repo: Path, *args: str, check: bool = True) -> str:
    return _run(["git", "-C", str(repo), *args], check=check).stdout.strip()


def _git_facts(repo: Path) -> dict:
    facts = {
        "source_head": None,
        "source_branch": None,
        "working_tree_clean": None,
        "origin": None,
    }
    if not shutil.which("git"):
        return facts
    try:
        facts["source_head"] = _git(repo, "rev-parse", "HEAD")
        facts["source_branch"] = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
        facts["working_tree_clean"] = not bool(_git(repo, "status", "--porcelain", "--untracked-files=all"))
        facts["origin"] = _git(repo, "remote", "get-url", "origin")
    except ContractError:
        pass
    return facts


def doctor_report() -> dict:
    install = inspect_installation()
    repo = Path(install.repo_path) if install.repo_path else None
    facts = _git_facts(repo) if repo else {
        "source_head": None,
        "source_branch": None,
        "working_tree_clean": None,
        "origin": None,
    }
    data_dir = Path(os.environ.get("RESIDUAL_DATA", str(Path.home() / ".residual" / "station"))).expanduser()
    database = data_dir / "station.sqlite3"
    git_available = bool(shutil.which("git"))

    blockers = []
    if not git_available:
        blockers.append("git_not_available")
    if install.method in {"editable", "source-checkout"}:
        if not repo:
            blockers.append("source_repo_not_resolved")
        elif facts["working_tree_clean"] is False:
            blockers.append("source_worktree_dirty")
        elif facts["source_branch"] not in {DEFAULT_BRANCH, None}:
            blockers.append("source_not_on_main")

    return {
        "residual_version": current_version(),
        "python": sys.version.split()[0],
        "python_executable": sys.executable,
        "residual_executable": shutil.which("residual"),
        "package_path": install.package_path,
        "install_method": install.method,
        "source_repo": install.repo_path,
        **facts,
        "git_available": git_available,
        "update_channel": "repository-main",
        "data_directory": str(data_dir),
        "state_directory_exists": data_dir.exists(),
        "database_exists": database.exists(),
        "update_readiness": "READY" if not blockers else "BLOCKED",
        "update_blockers": blockers,
    }


def format_doctor(report: dict) -> str:
    rows = [
        ("Version", report["residual_version"]),
        ("Python", report["python"]),
        ("Executable", report["residual_executable"] or "not found on PATH"),
        ("Package", report["package_path"]),
        ("Install method", report["install_method"]),
        ("Source repo", report["source_repo"] or "not resolved"),
        ("Source HEAD", report["source_head"] or "not available"),
        ("Source branch", report["source_branch"] or "not available"),
        ("Worktree clean", "yes" if report["working_tree_clean"] is True else "no" if report["working_tree_clean"] is False else "unknown"),
        ("Git", "available" if report["git_available"] else "missing"),
        ("Update channel", report["update_channel"]),
        ("Station data", report["data_directory"]),
        ("Station DB", "present" if report["database_exists"] else "not present"),
        ("Update readiness", report["update_readiness"]),
    ]
    width = max(len(k) for k, _ in rows)
    body = ["RESIDUAL Doctor", ""]
    body.extend(f"{k:<{width}}  {v}" for k, v in rows)
    if report["update_blockers"]:
        body.extend(["", "Blockers: " + ", ".join(report["update_blockers"])])
    return "\n".join(body)


def _target_ref(version: str | None) -> tuple[str, str]:
    if version:
        clean = version.removeprefix("v").strip()
        if not clean or any(ch not in "0123456789." for ch in clean):
            raise ContractError("update version must be numeric dotted form, for example 0.5.1")
        return f"v{clean}", f"refs/tags/v{clean}"
    return DEFAULT_BRANCH, f"refs/heads/{DEFAULT_BRANCH}"


def _remote_target(remote: str, ref: str) -> str:
    if not shutil.which("git"):
        raise ContractError("git is required for update checks")
    proc = _run(["git", "ls-remote", "--exit-code", remote, ref])
    line = next((line for line in proc.stdout.splitlines() if line.strip()), "")
    if not line:
        raise ContractError("requested update target was not found")
    return line.split()[0]


def update_status(*, version: str | None = None) -> dict:
    install = inspect_installation()
    target_name, ref = _target_ref(version)
    repo = Path(install.repo_path) if install.repo_path else None

    if repo:
        facts = _git_facts(repo)
        remote = facts["origin"] or REPOSITORY
        current = facts["source_head"]
    else:
        facts = {}
        remote = REPOSITORY
        current = None

    target = _remote_target(remote, ref)
    return {
        "install_method": install.method,
        "source_repo": install.repo_path,
        "current_version": current_version(),
        "current_revision": current,
        "target": target_name,
        "target_revision": target,
        "update_available": None if current is None else current != target,
        "channel": "repository-main" if version is None else "repository-tag",
    }


def perform_update(*, version: str | None = None) -> dict:
    install = inspect_installation()
    target_name, ref = _target_ref(version)
    repo = Path(install.repo_path) if install.repo_path else None

    if repo:
        facts = _git_facts(repo)
        if facts["working_tree_clean"] is not True:
            raise ContractError("source worktree is not clean; update refused")
        if version is None and facts["source_branch"] != DEFAULT_BRANCH:
            raise ContractError("source checkout must be on main for automatic update")
        remote = facts["origin"] or REPOSITORY
        target = _remote_target(remote, ref)
        before = facts["source_head"]
        if before == target:
            return {
                "updated": False,
                "install_method": install.method,
                "from_revision": before,
                "to_revision": target,
                "target": target_name,
                "message": "Already up to date.",
            }

        if version is not None:
            raise ContractError("version-pinned update is not supported for a live source checkout; use a clean release checkout")

        _run(["git", "-C", str(repo), "fetch", "--quiet", remote, DEFAULT_BRANCH])
        _run(["git", "-C", str(repo), "merge", "--ff-only", "FETCH_HEAD"])
        after = _git(repo, "rev-parse", "HEAD")
        if after != target:
            raise ContractError("updated source does not match the resolved remote target")

        if install.editable:
            _run([sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "-e", str(repo)])

        return {
            "updated": True,
            "install_method": install.method,
            "from_revision": before,
            "to_revision": after,
            "target": target_name,
            "state_directory": str(Path(os.environ.get("RESIDUAL_DATA", str(Path.home() / ".residual" / "station"))).expanduser()),
            "message": "Source updated with fast-forward-only semantics. RESIDUAL state was not modified.",
        }

    spec = f"git+{REPOSITORY}@{target_name}"
    before = current_version()
    _run([
        sys.executable, "-m", "pip", "install", "--disable-pip-version-check",
        "--upgrade", spec,
    ])
    check = _run([
        sys.executable, "-c",
        "from importlib.metadata import version; print(version('residual-agent-harness'))",
    ])
    return {
        "updated": True,
        "install_method": install.method,
        "from_version": before,
        "to_version": check.stdout.strip(),
        "target": target_name,
        "state_directory": str(Path(os.environ.get("RESIDUAL_DATA", str(Path.home() / ".residual" / "station"))).expanduser()),
        "message": "Package updated. RESIDUAL state was not modified.",
    }


def format_update(result: dict) -> str:
    if "target_revision" in result:
        availability = result["update_available"]
        status = "unknown" if availability is None else "yes" if availability else "no"
        return "\n".join([
            "RESIDUAL Update Check",
            "",
            f"Current version   {result['current_version']}",
            f"Current revision  {result['current_revision'] or 'not embedded in package install'}",
            f"Target            {result['target']}",
            f"Target revision   {result['target_revision']}",
            f"Update available  {status}",
        ])
    return result["message"]
