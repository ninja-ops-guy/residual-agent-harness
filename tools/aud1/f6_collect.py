#!/usr/bin/env python3
"""AUD-1 F6 physical diagnostics collector.

READ-ONLY with respect to Station state. It reads the Station SQLite database using
SQLite read-only mode, probes public HTTP metadata, records operator-supplied facts,
and freezes a hash manifest. It never issues claim/heartbeat/result/transition calls.

Run this tool from a separate tooling checkout/directory. The Station under test must
be the exact qualified candidate; --candidate-repo verifies that independently.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import platform
import re
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request

TARGET_SHA = "8df77b832b3839ccd2a6944a65760ce3ab10dc9c"
SCHEMA = "residual.aud1.f6.physical.v1"
SECRET_KEYS = {
    "session_token", "worker_token", "provider_credentials", "local_credentials",
    "api_key", "token", "secret", "password", "authorization", "cookie",
    "launch_url", "capability",
}
SENSITIVE_TEXT_PATTERNS = (
    re.compile(r"(?i)\b(?:authorization|api[_-]?key|token|secret|password|cookie)\s*[:=]\s*[^\s,;]+"),
    re.compile(r"(?i)\b(?:bearer|basic)\s+[A-Za-z0-9._~+/=-]{8,}"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"(?i)https?://[^\s]+/auth/[A-Za-z0-9._~%+-]{8,}"),
)
OPAQUE_SECRET_RE = re.compile(r"^[A-Za-z0-9._~+/=-]{32,}$")


def utcnow():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_bytes(value):
    return hashlib.sha256(value).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def atomic_json(path, value):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def redact_text(value):
    if not isinstance(value, str):
        return value
    redacted = value
    for pattern in SENSITIVE_TEXT_PATTERNS:
        redacted = pattern.sub("<redacted>", redacted)
    stripped = redacted.strip()
    if stripped == redacted and OPAQUE_SECRET_RE.fullmatch(stripped):
        # Evidence fields do not need opaque high-entropy scalar values. Fail closed
        # rather than risk retaining a credential stored under an unexpected key.
        return "<redacted>"
    return redacted


def redact(value, key=""):
    lowered = key.lower()
    if any(part in lowered for part in SECRET_KEYS):
        if isinstance(value, dict):
            return {str(k): "<redacted>" for k in value}
        if isinstance(value, list):
            return ["<redacted>"] * len(value)
        return "<redacted>"
    if isinstance(value, dict):
        return {str(k): redact(v, str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, str):
        return redact_text(value)
    return value


def run(command, cwd=None, timeout=15):
    try:
        p = subprocess.run(command, cwd=cwd, text=True, capture_output=True, timeout=timeout, check=False)
        return redact({"argv": command, "returncode": p.returncode, "stdout": p.stdout[-20000:], "stderr": p.stderr[-20000:]})
    except Exception as exc:
        return {"argv": command, "error": f"{type(exc).__name__}: {exc}"}


def candidate_identity(repo):
    repo = pathlib.Path(repo).resolve()
    head = run(["git", "rev-parse", "HEAD"], cwd=repo)
    status = run(["git", "status", "--porcelain=v1"], cwd=repo)
    tree = run(["git", "rev-parse", "HEAD^{tree}"], cwd=repo)
    actual = head.get("stdout", "").strip()
    return {
        "path": str(repo),
        "expected_sha": TARGET_SHA,
        "head_sha": actual,
        "tree_sha": tree.get("stdout", "").strip(),
        "tracked_or_untracked_changes": status.get("stdout", "").splitlines(),
        "exact_head": actual == TARGET_SHA,
        "clean_worktree": status.get("returncode") == 0 and not status.get("stdout", "").strip(),
        "git_errors": [x for x in (head.get("stderr"), tree.get("stderr"), status.get("stderr")) if x],
    }


def connect_ro(db):
    db = pathlib.Path(db).resolve()
    if not db.is_file():
        raise SystemExit(f"Station database not found: {db}")
    conn = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def parse_value(raw):
    try:
        return json.loads(raw)
    except Exception:
        return {"_unparsed": str(raw)[:1000]}


def station_snapshot(db, project, task=None):
    with connect_ro(db) as conn:
        project_row = conn.execute("SELECT value FROM projects WHERE id=?", (project,)).fetchone()
        if not project_row:
            raise SystemExit(f"Project not found: {project}")
        project_value = parse_value(project_row["value"])
        tasks = []
        query = "SELECT id,value FROM tasks WHERE project=?"
        params = [project]
        if task:
            query += " AND id=?"
            params.append(task)
        query += " ORDER BY id"
        for row in conn.execute(query, params):
            tasks.append({"id": row["id"], "value": parse_value(row["value"])})
        events = []
        for row in conn.execute(
            "SELECT seq,event_id,value,prev_hash,hash FROM events WHERE project=? ORDER BY seq", (project,)
        ):
            events.append({
                "seq": row["seq"], "event_id": row["event_id"], "value": parse_value(row["value"]),
                "prev_hash": row["prev_hash"], "hash": row["hash"],
            })
        settings = {}
        for row in conn.execute("SELECT id,value FROM settings ORDER BY id"):
            settings[row["id"]] = redact(parse_value(row["value"]), row["id"])
        submissions = conn.execute("SELECT COUNT(*) AS n FROM submissions").fetchone()["n"]
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    return {
        "captured_at": utcnow(),
        "project_id": project,
        "project": project_value,
        "tasks": tasks,
        "events": events,
        "event_tail": events[-30:],
        "event_count": len(events),
        "settings_redacted": settings,
        "submission_count_global": submissions,
        "sqlite_integrity": integrity,
    }


def public_probe(url):
    target = url.rstrip("/") + "/api/bootstrap"
    req = urllib.request.Request(target, headers={"User-Agent": "residual-aud1-f6-diagnostics/1"})
    started = time.monotonic()
    try:
        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req, timeout=10) as response:
            raw = response.read(100_000)
            elapsed = time.monotonic() - started
            body = json.loads(raw) if raw else None
            serialized = canonical(body)
            suspicious = any(k in serialized.lower() for k in ('"session_token"', '"worker_token"'))
            return {
                "url": target, "status": response.status, "elapsed_ms": round(elapsed * 1000, 1),
                "body": redact(body), "authority_key_names_present": suspicious,
            }
    except urllib.error.HTTPError as exc:
        return {"url": target, "status": exc.code, "elapsed_ms": round((time.monotonic()-started)*1000, 1)}
    except Exception as exc:
        return {"url": target, "error": f"{type(exc).__name__}: {exc}", "elapsed_ms": round((time.monotonic()-started)*1000, 1)}


def environment_snapshot():
    return {
        "captured_at": utcnow(),
        "hostname": platform.node(),
        "platform": platform.platform(),
        "python": sys.version,
        "pid": os.getpid(),
        "time_monotonic": time.monotonic(),
    }


def bundle_dir(root, case_id):
    return pathlib.Path(root).resolve() / case_id


def capture(args):
    out = bundle_dir(args.output, args.case)
    out.mkdir(parents=True, exist_ok=True)
    seq = len(list(out.glob("snapshot-*.json"))) + 1
    identity = candidate_identity(args.candidate_repo)
    if not identity["exact_head"]:
        raise SystemExit(f"REFUSE: candidate repo is {identity['head_sha']!r}, expected {TARGET_SHA}")
    if not identity["clean_worktree"]:
        raise SystemExit("REFUSE: candidate repo worktree is not clean")
    payload = {
        "schema": SCHEMA,
        "case": args.case,
        "label": args.label,
        "candidate": identity,
        "environment": environment_snapshot(),
        "station": station_snapshot(args.db, args.project, args.task),
        "public_probe": public_probe(args.station_url) if args.station_url else None,
    }
    path = out / f"snapshot-{seq:03d}-{args.label}.json"
    atomic_json(path, payload)
    print(path)
    return 0


def note(args):
    out = bundle_dir(args.output, args.case)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "operator-ledger.jsonl"
    entry = {
        "schema": SCHEMA,
        "timestamp": utcnow(),
        "case": args.case,
        "kind": args.kind,
        "message": redact_text(args.message),
    }
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(canonical(entry) + "\n")
    print(path)
    return 0


def record_command(args):
    out = bundle_dir(args.output, args.case)
    out.mkdir(parents=True, exist_ok=True)
    if not args.command:
        raise SystemExit("record-command requires a command after --")
    command = args.command[1:] if args.command and args.command[0] == "--" else args.command
    result = {
        "schema": SCHEMA,
        "timestamp": utcnow(),
        "case": args.case,
        "name": args.name,
        "environment": environment_snapshot(),
        "result": run(command, timeout=args.timeout),
    }
    path = out / f"command-{args.name}.json"
    atomic_json(path, result)
    print(path)
    return 0


def sanitize_attachment(source):
    raw = source.read_bytes()
    source_hash = sha256_bytes(raw)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SystemExit(
            "REFUSE: non-UTF-8 attachment content is not stored by the evidence kit; "
            "retain its SHA-256 separately and provide a reviewed textual export instead"
        ) from exc
    try:
        parsed = json.loads(text)
    except Exception:
        clean_text = redact_text(text)
        stored = clean_text.encode("utf-8")
    else:
        stored = (json.dumps(redact(parsed), indent=2, sort_keys=True) + "\n").encode("utf-8")
    return stored, source_hash, stored != raw


def attach(args):
    out = bundle_dir(args.output, args.case)
    out.mkdir(parents=True, exist_ok=True)
    source = pathlib.Path(args.file).resolve()
    if not source.is_file():
        raise SystemExit(f"Attachment not found: {source}")
    safe_name = "".join(ch for ch in (args.name or source.name) if ch.isalnum() or ch in "._-")[:160]
    if not safe_name:
        raise SystemExit("Attachment name is empty after sanitization")
    destination = out / "attachments" / safe_name
    destination.parent.mkdir(parents=True, exist_ok=True)
    stored, source_hash, redacted_content = sanitize_attachment(source)
    if redacted_content:
        destination.write_bytes(stored)
    else:
        shutil.copyfile(source, destination)
    record = {
        "schema": SCHEMA,
        "attached_at": utcnow(),
        "source_name": source.name,
        "destination": destination.relative_to(out).as_posix(),
        "source_sha256": source_hash,
        "stored_bytes": destination.stat().st_size,
        "stored_sha256": sha256_file(destination),
        "redacted_content": redacted_content,
    }
    atomic_json(destination.with_suffix(destination.suffix + ".meta.json"), record)
    print(json.dumps(record, indent=2))
    return 0


def freeze(args):
    out = bundle_dir(args.output, args.case)
    if not out.is_dir():
        raise SystemExit(f"Case directory not found: {out}")
    files = []
    for path in sorted(p for p in out.rglob("*") if p.is_file() and p.name not in {"manifest.json", "manifest.sha256"}):
        files.append({"path": path.relative_to(out).as_posix(), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {
        "schema": SCHEMA,
        "case": args.case,
        "frozen_at": utcnow(),
        "target_sha": TARGET_SHA,
        "files": files,
    }
    manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    (out / "manifest.json").write_bytes(manifest_bytes)
    digest = sha256_bytes(manifest_bytes)
    (out / "manifest.sha256").write_text(f"{digest}  manifest.json\n", encoding="utf-8")
    print(f"{digest}  {out / 'manifest.json'}")
    return 0


def verify(args):
    out = bundle_dir(args.output, args.case)
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    errors = []
    for item in manifest["files"]:
        path = out / item["path"]
        if not path.is_file():
            errors.append(f"missing: {item['path']}")
        elif sha256_file(path) != item["sha256"]:
            errors.append(f"hash mismatch: {item['path']}")
    expected_line = (out / "manifest.sha256").read_text(encoding="utf-8").split()[0]
    actual_manifest = sha256_file(out / "manifest.json")
    if expected_line != actual_manifest:
        errors.append("manifest hash mismatch")
    result = {"verified_at": utcnow(), "case": args.case, "ok": not errors, "errors": errors, "manifest_sha256": actual_manifest}
    print(json.dumps(result, indent=2))
    return 0 if not errors else 2


def parser():
    p = argparse.ArgumentParser(description="Read-only AUD-1 F6 physical evidence collector")
    p.add_argument("--output", default="AUD1-F6-EVIDENCE")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("capture")
    c.add_argument("--case", required=True, choices=["F6-A-inside-window", "F6-B-outside-window"])
    c.add_argument("--label", required=True)
    c.add_argument("--candidate-repo", required=True)
    c.add_argument("--db", required=True, help="Path to station.sqlite3 on the Station host")
    c.add_argument("--project", required=True)
    c.add_argument("--task")
    c.add_argument("--station-url", default="")
    c.set_defaults(func=capture)

    n = sub.add_parser("note")
    n.add_argument("--case", required=True, choices=["F6-A-inside-window", "F6-B-outside-window"])
    n.add_argument("--kind", required=True, choices=["HITL", "TUNNEL_DOWN", "TUNNEL_UP", "OBSERVATION", "REASSIGNMENT", "STALE_RESULT", "ERROR"])
    n.add_argument("--message", required=True)
    n.set_defaults(func=note)

    r = sub.add_parser("record-command")
    r.add_argument("--case", required=True, choices=["F6-A-inside-window", "F6-B-outside-window"])
    r.add_argument("--name", required=True)
    r.add_argument("--timeout", type=int, default=30)
    r.add_argument("command", nargs=argparse.REMAINDER)
    r.set_defaults(func=record_command)

    a = sub.add_parser("attach")
    a.add_argument("--case", required=True, choices=["F6-A-inside-window", "F6-B-outside-window"])
    a.add_argument("--file", required=True)
    a.add_argument("--name", default="")
    a.set_defaults(func=attach)

    f = sub.add_parser("freeze")
    f.add_argument("--case", required=True, choices=["F6-A-inside-window", "F6-B-outside-window"])
    f.set_defaults(func=freeze)

    v = sub.add_parser("verify")
    v.add_argument("--case", required=True, choices=["F6-A-inside-window", "F6-B-outside-window"])
    v.set_defaults(func=verify)
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())