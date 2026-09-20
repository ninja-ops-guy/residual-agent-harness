"""Small, explicit LDD workflow contract. Markdown is an import/export view."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from datetime import datetime

from residual.core import ContractError, canonical, strict_json

STATES = ("proposed", "triaging", "ready", "running", "repair_required", "blocked",
          "local_verified", "review_ready", "approved", "integrated")
TRANSITIONS = {
    "proposed": {"triaging"}, "triaging": {"ready", "blocked"},
    "ready": {"running", "blocked"}, "running": {"local_verified", "repair_required", "blocked"},
    "repair_required": {"ready", "running", "blocked"}, "blocked": {"proposed", "ready"},
    "local_verified": {"review_ready"}, "review_ready": {"approved", "repair_required", "blocked"},
    "approved": {"integrated", "repair_required", "blocked"}, "integrated": set(),
}
ID = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
SHA = re.compile(r"^[a-f0-9]{40,64}$")
EVENT_TYPES = {"project.created", "project.paused", "project.resumed", "task.transition",
               "task.claimed", "task.finding", "checks.completed", "review.completed",
               "integration.completed", "usage.recorded", "report.generated", "release.exported",
               "worker.joined", "worker.expired", "project.note", "slm.observation_failed"}
LDD_BASE = json.loads((Path(__file__).parent / "schemas" / "ldd-base.json").read_text())


def bounded(value, name, maximum=4000, empty=False):
    if not isinstance(value, str) or (not empty and not value.strip()) or len(value) > maximum:
        raise ContractError(f"{name} must be text of 1–{maximum} characters")
    return value.strip()


def path_ok(path):
    if not isinstance(path, str) or not path or len(path) > 240 or "\\" in path or "\x00" in path:
        raise ContractError("Use a relative POSIX file path")
    parts = PurePosixPath(path).parts
    if PurePosixPath(path).is_absolute() or any(p in {"..", ".git", ".residual", ".env"} for p in parts):
        raise ContractError("Path escapes the workspace or names a protected file")
    if any(p.startswith(".env.") and p not in {".env.example", ".env.template"} for p in parts) or path.startswith("-") or ":" in path:
        raise ContractError("Protected or invalid file path")
    return path


def parse_spec(markdown):
    bounded(markdown, "Specification", 250_000)
    blocks = re.findall(r"```(?:json|ldd)\s*\n(.*?)\n```", markdown, re.S)
    if len(blocks) != 1:
        raise ContractError("Include exactly one fenced json or ldd project manifest. Use the example template.")
    manifest = strict_json(blocks[0])
    if not isinstance(manifest, dict) or set(manifest) - {"schema_version", "name", "goal", "tasks"}:
        raise ContractError("Unknown project manifest fields")
    if type(manifest.get("schema_version")) is not int or manifest.get("schema_version") != 1:
        raise ContractError("schema_version must be 1")
    bounded(manifest.get("name"), "Project name", 100)
    bounded(manifest.get("goal"), "Project goal", 4000)
    tasks = manifest.get("tasks")
    if not isinstance(tasks, list) or not 1 <= len(tasks) <= 100:
        raise ContractError("A project needs 1–100 tasks")
    ids = set()
    for task in tasks:
        if not isinstance(task, dict) or set(task) - {"id", "title", "instruction", "depends_on", "files", "context", "checks", "route"}:
            raise ContractError("Unknown task fields")
        tid = task.get("id", "")
        if not isinstance(tid, str) or not ID.fullmatch(tid) or tid in ids:
            raise ContractError("Task IDs must be unique letters, digits, underscores, or hyphens")
        ids.add(tid)
        bounded(task.get("title"), "Task title", 160)
        bounded(task.get("instruction"), "Task instruction", 12000)
        if task.get("route", "local") not in {"local", "cloud"}:
            raise ContractError("route must be local or cloud")
        task.setdefault("route", "local")
        for key in ("files", "context"):
            value = task.setdefault(key, [])
            if not isinstance(value, list) or len(value) > 30 or len(set(value)) != len(value):
                raise ContractError(f"{key} must contain at most 30 unique paths")
            for p in value:
                path_ok(p)
        if not task["files"]:
            raise ContractError("Each implementation task needs an explicit writable file list")
        deps = task.setdefault("depends_on", [])
        if not isinstance(deps, list) or any(not isinstance(d, str) for d in deps) or len(set(deps)) != len(deps):
            raise ContractError("depends_on must be a list of unique task IDs")
        checks = task.get("checks")
        if not isinstance(checks, list) or not 1 <= len(checks) <= 20:
            raise ContractError("Each task needs 1–20 deterministic acceptance checks")
        for check in checks:
            if not isinstance(check, dict):
                raise ContractError("Invalid check")
            kind = check.get("kind")
            allowed = {"exists": {"kind", "path"}, "contains": {"kind", "path", "text"},
                       "python_compile": {"kind", "path"}, "json_valid": {"kind", "path"},
                       "command": {"kind", "argv", "timeout"}}
            if kind not in allowed or set(check) - allowed[kind]:
                raise ContractError("Unsupported check or check field")
            if kind == "command":
                argv = check.get("argv")
                if not isinstance(argv, list) or not 1 <= len(argv) <= 30 or any(not isinstance(x, str) or not x or "\x00" in x or len(x) > 2000 for x in argv):
                    raise ContractError("Command checks require an argument array, without a shell")
                if type(check.get("timeout", 60)) is not int or not 1 <= check.get("timeout", 60) <= 300:
                    raise ContractError("Check timeout must be 1–300 seconds")
            else:
                path_ok(check.get("path"))
                if kind == "contains":
                    bounded(check.get("text"), "Check text", 10000)
    graph = {t["id"]: t["depends_on"] for t in tasks}
    visiting, visited = set(), set()
    def visit(tid):
        if tid not in ids or tid in visiting:
            raise ContractError("Task dependencies contain a cycle or an unknown ID")
        if tid in visited:
            return
        visiting.add(tid)
        for dep in graph[tid]:
            visit(dep)
        visiting.remove(tid)
        visited.add(tid)
    for tid in ids:
        visit(tid)
    return manifest


def event_validate(event):
    """LDD BaseEvent plus strict workflow envelope; applied before DB admission."""
    if not isinstance(event, dict) or not set(LDD_BASE["required"]).issubset(event):
        raise ContractError("Missing LDD BaseEvent fields")
    required = {"schema_version", "event_id", "event_type", "timestamp", "project_id", "task_id",
                "actor", "attempt", "spec_hash", "data"}
    if not isinstance(event, dict) or set(event) != required or type(event["schema_version"]) is not int or event["schema_version"] != 1:
        raise ContractError("Invalid LDD event envelope")
    if event["event_type"] not in EVENT_TYPES:
        raise ContractError("Unknown LDD event type")
    for key in ("event_id", "timestamp", "project_id", "actor", "spec_hash"):
        bounded(event[key], key, 200)
    if not re.fullmatch(r"[a-f0-9]{64}", event["spec_hash"]):
        raise ContractError("Event must reference a specification SHA-256")
    try:
        stamp = datetime.fromisoformat(event["timestamp"])
        if stamp.tzinfo is None:
            raise ValueError()
    except ValueError:
        raise ContractError("LDD timestamps must be timezone-aware ISO 8601") from None
    if event["task_id"] is not None and not ID.fullmatch(event["task_id"]):
        raise ContractError("Invalid task ID")
    if type(event["attempt"]) is not int or event["attempt"] < 0 or not isinstance(event["data"], dict):
        raise ContractError("Invalid attempt or event data")
    if len(canonical(event).encode()) > 24_000:
        raise ContractError("Workflow events must stay under 24 KB; store larger evidence as artifacts")


def sha(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()
