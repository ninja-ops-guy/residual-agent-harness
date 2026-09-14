from __future__ import annotations

import argparse
import ctypes.util
import json
import os
import platform
import subprocess
import tempfile
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from residual.core import strict_json


class DoctorError(RuntimeError):
    pass


def _run(argv: list[str], *, timeout: float = 10.0, cwd: Path | None = None) -> tuple[int, str, str]:
    try:
        p = subprocess.run(argv, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           text=True, timeout=timeout, check=False)
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, "", type(exc).__name__


def _json_get(url: str, *, timeout: float = 10.0) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.load(response)


def _json_post(url: str, payload: dict, *, timeout: float = 120.0) -> dict:
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.load(response)


def _model_digest(base_url: str, model: str) -> str:
    payload = _json_get(base_url.rstrip("/") + "/api/tags")
    for item in payload.get("models", []):
        if item.get("name") == model or item.get("model") == model:
            digest = item.get("digest")
            if isinstance(digest, str) and digest:
                return digest
    raise DoctorError(f"model {model!r} is not installed")


def _canary(base_url: str, model: str, seed: int = 7) -> dict:
    started = time.monotonic()
    payload = _json_post(base_url.rstrip("/") + "/api/chat", {
        "model": model,
        "messages": [{"role": "user", "content": "Return exactly JSON: {\"ok\":true}"}],
        "stream": False,
        "format": {"type": "object", "properties": {"ok": {"type": "boolean"}},
                   "required": ["ok"], "additionalProperties": False},
        "options": {"temperature": 0, "seed": seed},
    })
    message = payload.get("message") or {}
    parsed = strict_json(str(message.get("content", "")))
    if parsed != {"ok": True}:
        raise DoctorError("Ollama canary returned unexpected structured output")
    prompt = payload.get("prompt_eval_count")
    completion = payload.get("eval_count")
    if type(prompt) is not int or type(completion) is not int:
        raise DoctorError("Ollama canary lacks token accounting")
    return {
        "ok": True,
        "elapsed_s": time.monotonic() - started,
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": prompt + completion,
        "eval_duration_ns": int(payload.get("eval_duration") or 0),
    }


def _calibrate(base_url: str, model: str, widths: tuple[int, ...]) -> dict:
    rows = []
    best_width = 1
    best_rate = -1.0
    for width in widths:
        started = time.monotonic()
        results = []
        with ThreadPoolExecutor(max_workers=width) as pool:
            futs = [pool.submit(_canary, base_url, model, 7 + i) for i in range(width)]
            for fut in as_completed(futs):
                results.append(fut.result())
        elapsed = max(time.monotonic() - started, 1e-9)
        tokens = sum(r["total_tokens"] for r in results)
        rate = tokens / elapsed
        rows.append({"width": width, "elapsed_s": elapsed, "aggregate_tokens_per_s": rate,
                     "requests": len(results)})
        if rate > best_rate:
            best_rate, best_width = rate, width
    return {"recommended_workers": best_width, "measurements": rows}


def _git_probe(repo: Path) -> dict:
    rc, git_version, _ = _run(["git", "--version"])
    if rc:
        raise DoctorError("git is unavailable")
    rc, root, _ = _run(["git", "rev-parse", "--show-toplevel"], cwd=repo)
    if rc:
        raise DoctorError("current directory is not a git repository")
    rc, dirty, _ = _run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=repo)
    if rc:
        raise DoctorError("git status failed")
    with tempfile.TemporaryDirectory(prefix="residual-doctor-worktree-") as td:
        work = Path(td) / "probe"
        rc, _, err = _run(["git", "worktree", "add", "--detach", str(work), "HEAD"], cwd=repo, timeout=30)
        if rc:
            raise DoctorError(f"git worktree probe failed: {err}")
        _run(["git", "worktree", "remove", "--force", str(work)], cwd=repo, timeout=30)
    return {"version": git_version, "root": root, "tracked_clean": dirty == "", "worktree": True}


def collect_profile(*, model: str | None = None, base_url: str = "http://localhost:11434",
                    canary: bool = False, calibrate: bool = False,
                    widths: tuple[int, ...] = (1, 2, 4, 6)) -> dict:
    checks = {}
    checks["python"] = {"ok": True, "version": platform.python_version(),
                        "implementation": platform.python_implementation()}
    checks["git"] = {"ok": True, **_git_probe(Path.cwd())}
    checks["crypto"] = {"ok": ctypes.util.find_library("crypto") is not None}
    checks["seccomp"] = {"ok": ctypes.util.find_library("seccomp") is not None}
    checks["pidfd"] = {"ok": hasattr(os, "pidfd_open")}
    checks["hardware"] = {"ok": True, "system": platform.system(), "release": platform.release(),
                          "machine": platform.machine(), "logical_cpus": os.cpu_count()}
    if model:
        version = _model_digest(base_url, model)
        checks["ollama"] = {"ok": True, "base_url": base_url, "model": model, "model_digest": version}
        if canary or calibrate:
            checks["canary"] = _canary(base_url, model)
        if calibrate:
            checks["calibration"] = {"ok": True, **_calibrate(base_url, model, widths)}
    required = ["python", "git", "crypto", "seccomp", "pidfd"] + (["ollama"] if model else [])
    ready = all(bool(checks[name].get("ok")) for name in required)
    return {"schema_version": "factory-host-profile-v1", "status": "ready" if ready else "not_ready",
            "checks": checks,
            "recommended_workers": (checks.get("calibration") or {}).get("recommended_workers")}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="residual doctor", description="Validate Factory first-run prerequisites")
    p.add_argument("--model")
    p.add_argument("--base-url", default="http://localhost:11434")
    p.add_argument("--canary", action="store_true")
    p.add_argument("--calibrate-concurrency", action="store_true")
    p.add_argument("--widths", default="1,2,4,6")
    p.add_argument("--json", dest="json_path")
    args = p.parse_args(argv)
    try:
        widths = tuple(int(x) for x in args.widths.split(",") if x.strip())
        if any(x < 1 or x > 64 for x in widths) or len(set(widths)) != len(widths):
            raise DoctorError("invalid concurrency widths")
        profile = collect_profile(model=args.model, base_url=args.base_url,
                                  canary=args.canary or args.calibrate_concurrency,
                                  calibrate=args.calibrate_concurrency, widths=widths)
        text = json.dumps(profile, indent=2, sort_keys=True)
        print(text)
        if args.json_path:
            path = Path(args.json_path); path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text + "\n", encoding="utf-8")
        return 0 if profile["status"] == "ready" else 2
    except Exception as exc:
        print(json.dumps({"schema_version": "factory-host-profile-v1", "status": "not_ready",
                          "error": f"{type(exc).__name__}: {exc}"}, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
