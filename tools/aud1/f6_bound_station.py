#!/usr/bin/env python3
"""Launch the exact AUD-1 candidate Station and emit a process-binding witness.

This helper lives on the diagnostics/tooling branch. It never modifies the candidate
checkout. It verifies exact SHA + clean worktree, resolves the Station module from that
checkout, records the live process identity, then executes the candidate module in the
same Python process.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import os
import pathlib
import runpy
import subprocess
import sys

TARGET_SHA = "8df77b832b3839ccd2a6944a65760ce3ab10dc9c"
SCHEMA = "residual.aud1.f6.station-launch.v1"


def utcnow():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def git(repo, *args):
    p = subprocess.run(["git", *args], cwd=repo, text=True, capture_output=True, check=False)
    if p.returncode:
        raise SystemExit(f"git {' '.join(args)} failed: {p.stderr.strip()}")
    return p.stdout.strip()


def atomic_json(path, value):
    path = pathlib.Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    digest = sha256_file(path)
    pathlib.Path(str(path) + ".sha256").write_text(f"{digest}  {path.name}\n", encoding="ascii")
    return digest


def main(argv=None):
    parser = argparse.ArgumentParser(description="Launch exact #399 Station with a process-binding witness")
    parser.add_argument("--candidate-repo", required=True)
    parser.add_argument("--launch-record", required=True)
    parser.add_argument("--data", required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--open", action="store_true")
    parser.add_argument("--start-ollama", action="store_true")
    args = parser.parse_args(argv)

    repo = pathlib.Path(args.candidate_repo).resolve()
    if not repo.is_dir():
        raise SystemExit(f"Candidate repo not found: {repo}")
    head = git(repo, "rev-parse", "HEAD")
    if head != TARGET_SHA:
        raise SystemExit(f"REFUSE: candidate is {head}; expected {TARGET_SHA}")
    if git(repo, "status", "--porcelain=v1"):
        raise SystemExit("REFUSE: candidate checkout is dirty")
    tree = git(repo, "rev-parse", "HEAD^{tree}")

    # Force import resolution from the exact candidate checkout, not from the tooling
    # checkout or a globally installed residual package.
    sys.path.insert(0, str(repo))
    spec = importlib.util.find_spec("residual.station.server")
    if spec is None or not spec.origin:
        raise SystemExit("Could not resolve residual.station.server from candidate checkout")
    module_path = pathlib.Path(spec.origin).resolve()
    try:
        module_path.relative_to(repo)
    except ValueError as exc:
        raise SystemExit(f"REFUSE: Station module resolved outside candidate checkout: {module_path}") from exc

    data = pathlib.Path(args.data).resolve()
    data.mkdir(parents=True, exist_ok=True)
    station_url = f"http://{args.host}:{args.port}"
    record = {
        "schema": SCHEMA,
        "created_at": utcnow(),
        "pid": os.getpid(),
        "python_executable": sys.executable,
        "candidate_repo": str(repo),
        "candidate_head": head,
        "candidate_tree": tree,
        "server_module": str(module_path),
        "server_module_sha256": sha256_file(module_path),
        "station_data": str(data),
        "station_url": station_url,
        "host": args.host,
        "port": args.port,
        "open_requested": bool(args.open),
        "start_ollama_requested": bool(args.start_ollama),
    }
    digest = atomic_json(args.launch_record, record)
    print(f"F6 Station launch witness: {pathlib.Path(args.launch_record).resolve()}", flush=True)
    print(f"F6 Station launch witness SHA256: {digest}", flush=True)
    print(f"F6 Station PID: {os.getpid()}", flush=True)

    os.chdir(repo)
    server_argv = ["residual.station.server", "--host", args.host, "--port", str(args.port), "--data", str(data)]
    if args.open:
        server_argv.append("--open")
    if args.start_ollama:
        server_argv.append("--start-ollama")
    sys.argv = server_argv
    runpy.run_module("residual.station.server", run_name="__main__", alter_sys=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
