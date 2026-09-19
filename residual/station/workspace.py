"""Isolated Git candidates and deterministic acceptance checks."""
from __future__ import annotations

import ast
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
import zipfile
from pathlib import Path

from residual.core import ContractError, canonical, strict_json
from .contracts import path_ok


def git(root, *args, timeout=60):
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_CONFIG_NOSYSTEM": "1"}
    proc = subprocess.run(["git", "-c", "core.hooksPath=" + os.devnull, "-c", "commit.gpgsign=false", "-C", str(root), *args],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, env=env)
    if proc.returncode:
        raise ContractError("Git operation failed. Check that the repository exists, has a commit, and the candidate has no conflicts.")
    return proc.stdout.decode("utf-8", errors="replace").rstrip()


def safe_file(root, name):
    path_ok(name)
    root = Path(root).resolve()
    target = root / name
    # Even an in-root symlink is forbidden: models must only edit ordinary scoped files.
    check = target
    while check != root:
        if check.is_symlink():
            raise ContractError("Symlinks are not supported in task file scope")
        check = check.parent
    if not target.resolve().is_relative_to(root):
        raise ContractError("File path escapes workspace")
    return target


def init_repo(root, files=None):
    root = Path(root); root.mkdir(parents=True, exist_ok=True)
    git(root, "init", "-b", "main")
    git(root, "config", "user.name", "RESIDUAL Runner")
    git(root, "config", "user.email", "runner@residual.local")
    for name, value in (files or {"README.md": "# Project workspace\n"}).items():
        target = safe_file(root, name); target.parent.mkdir(parents=True, exist_ok=True); target.write_text(value, encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "-m", "Initialize project workspace")
    return root


def clone_repo(source, destination):
    source = Path(source).expanduser().resolve()
    if not source.is_dir():
        raise ContractError("Choose an existing local Git repository path")
    git(source, "rev-parse", "HEAD")
    if git(source, "status", "--porcelain"):
        raise ContractError("Commit or stash repository changes before importing; runners start from committed files")
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    git(destination.parent, "clone", "--no-hardlinks", "--", str(source), str(destination))
    git(destination, "config", "user.name", "RESIDUAL Runner")
    git(destination, "config", "user.email", "runner@residual.local")
    git(destination, "remote", "remove", "origin")
    return destination


def candidate(repo, directory):
    base = git(repo, "rev-parse", "HEAD")
    git(repo, "worktree", "add", "--detach", str(directory), base)
    return base


def context_files(root, task, budget=100_000):
    files, used = {}, 0
    for name in dict.fromkeys(task["context"] + task["files"]):
        path = safe_file(root, name)
        if not path.exists():
            files[name] = None
            continue
        if not path.is_file() or path.stat().st_size > 80_000:
            raise ContractError("A scoped file exceeds 80 KB. Split the task or narrow its scope.")
        try:
            value = path.read_text(encoding="utf-8")
        except UnicodeError:
            raise ContractError("Runner scope supports UTF-8 text files") from None
        used += len(value.encode())
        if used > budget:
            raise ContractError("Scoped context exceeds 100 KB. Split the task.")
        files[name] = value
    return files


def apply_files(root, task, values):
    if not isinstance(values, dict) or not values or set(values) - set(task["files"]):
        raise ContractError("Candidate must only update explicitly writable task files")
    if sum(len(v.encode()) if isinstance(v, str) else 10**9 for v in values.values()) > 200_000:
        raise ContractError("Candidate file content must be UTF-8 text under 200 KB")
    # Validate all names before making any edit; file deletion intentionally excluded.
    for name in values:
        safe_file(root, name)
    for name, value in values.items():
        p = safe_file(root, name); p.parent.mkdir(parents=True, exist_ok=True); p.write_text(value, encoding="utf-8")


def run_checks(root, checks, commands=False):
    results = []
    for i, check in enumerate(checks):
        started = time.monotonic()
        kind = check["kind"]
        result = {"id": f"check-{i + 1}", "kind": kind, "passed": False, "detail": ""}
        try:
            if kind == "command":
                if not commands:
                    raise ContractError("Project test commands are disabled; enable them for this trusted project at import")
                argv = [sys.executable if x == "{python}" else x for x in check["argv"]]
                env = {k: v for k, v in os.environ.items() if k in {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "LANG"}}
                # Isolated HOME and stripped API keys; this is process isolation, not an OS sandbox.
                with tempfile.TemporaryDirectory(prefix="residual-check-") as home:
                    env.update(HOME=home, USERPROFILE=home, PYTHONDONTWRITEBYTECODE="1", PYTHONUNBUFFERED="1")
                    with tempfile.TemporaryFile() as output:
                        p = subprocess.Popen(argv, cwd=root, env=env, stdout=output, stderr=subprocess.STDOUT,
                                             start_new_session=(os.name != "nt"))
                        try:
                            p.wait(timeout=check.get("timeout", 60))
                        except subprocess.TimeoutExpired:
                            if os.name == "nt":
                                p.kill()
                            else:
                                import signal
                                os.killpg(p.pid, signal.SIGKILL)
                            p.wait()
                            raise ContractError("Acceptance command timed out") from None
                        output.seek(0)
                        raw = output.read(24_001)
                        result["detail"] = raw[:24000].decode("utf-8", errors="replace")
                        result["output_truncated"] = len(raw) > 24000
                        result["passed"] = p.returncode == 0
                        result["exit_code"] = p.returncode
            else:
                path = safe_file(root, check["path"])
                if not path.is_file():
                    raise ContractError("Required file does not exist")
                if path.stat().st_size > 1_000_000:
                    raise ContractError("Acceptance file exceeds 1 MB")
                if kind == "contains" and check["text"] not in path.read_text(encoding="utf-8"):
                    raise ContractError("Required text was not found")
                if kind == "python_compile":
                    ast.parse(path.read_text(encoding="utf-8"), filename=check["path"])
                parsed_json = None
                if kind in {"json_valid", "json_value", "json_exact"}:
                    parsed_json = strict_json(path.read_text(encoding="utf-8"))
                if kind == "json_exact":
                    if canonical(parsed_json) != canonical(check.get("value")):
                        raise ContractError("JSON document did not exactly match the required value")
                if kind == "json_value":
                    current = parsed_json
                    for key in check["pointer"]:
                        if not isinstance(current, dict) or key not in current:
                            raise ContractError("Required JSON value was not found")
                        current = current[key]
                    if canonical(current) != canonical(check.get("value")):
                        raise ContractError("JSON value did not match the required value")
                result.update(passed=True, detail="Acceptance check passed")
        except (ContractError, OSError, ValueError, SyntaxError, UnicodeError) as e:
            result["detail"] = str(e)[:1000]
        result["elapsed_ms"] = round((time.monotonic() - started) * 1000)
        results.append(result)
    return results


def commit_candidate(root, task):
    # Check commands may not silently alter undeclared files or acceptance fixtures.
    allowed = set(task["files"])
    changed = git(root, "status", "--porcelain", "--untracked-files=all", "-z")
    for line in changed.split("\0"):
        if len(line) > 3 and line[3:] not in allowed:
            raise ContractError("Candidate or test command modified files outside the task write scope")
    git(root, "add", "--", *task["files"])
    git(root, "commit", "--allow-empty", "-m", f"Implement {task['id']}: {task['title']}")
    return git(root, "rev-parse", "HEAD")


def export_zip(repo, commit="HEAD"):
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w", zipfile.ZIP_DEFLATED) as z:
        for name in git(repo, "ls-tree", "-r", "--name-only", "-z", commit).split("\0"):
            if not name:
                continue
            path_ok(name)
            p = safe_file(repo, name)
            if p.is_file():
                # Read the accepted Git object, never mutable working-tree bytes.
                value = subprocess.check_output(["git", "-C", str(repo), "show", f"{commit}:{name}"])
                z.writestr(name, value)
    return data.getvalue()
