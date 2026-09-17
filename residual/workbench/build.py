"""Generate reviewable files through the real RESIDUAL Harness without executing them.

Browser example: Mission Control invokes this module with a fixed argv array.
CLI example:
  mission build "Build a calculator" --config provider.toml --allow-cloud

Accepted files are written only below runs/missions/<id>/artifacts/. They are not
executed, imported, applied to the repository, or treated as semantically correct.
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import signal
import sys
import uuid

from residual.config import build_harness, load_config
from residual.core import Artifact, ContractError, Obligation, Registry, Task, Verdict, canonical
from residual.engine import Limits
from .runner import (MailboxProvider, ObservedHarness, WorkbenchDeadline, read_json,
                     register as register_common, save, source_snapshot, verify_run)

MAX_BUILD_FILES = 8
MAX_BUILD_FILE_BYTES = 48000
MAX_BUILD_TOTAL_BYTES = 128000
MAX_BUILD_OUTPUT_TOKENS = 8192
SAFE_PATH = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,119}\Z")
ID = re.compile(r"m-[0-9a-f]{32}\Z")


def safe_artifact_path(value: str) -> PurePosixPath:
    if not isinstance(value, str) or not SAFE_PATH.fullmatch(value) or "\\" in value or "//" in value:
        raise ContractError("generated artifact path is not a safe relative text path")
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} or part.startswith(".") for part in path.parts):
        raise ContractError("generated artifact path is not a safe relative text path")
    return path


def validate_bundle(value, required_text=()):
    if not isinstance(value, dict) or set(value) != {"summary", "files"}:
        return "build_shape"
    summary, files = value["summary"], value["files"]
    if not isinstance(summary, str) or not summary.strip() or len(summary.encode("utf-8")) > 4000:
        return "build_summary"
    if not isinstance(files, list) or not 1 <= len(files) <= MAX_BUILD_FILES:
        return "build_file_count"
    seen, total, searchable = set(), 0, [summary]
    for item in files:
        if not isinstance(item, dict) or set(item) != {"path", "content"}:
            return "build_file_shape"
        try:
            path = str(safe_artifact_path(item["path"]))
        except ContractError:
            return "build_file_path"
        if path in seen:
            return "build_duplicate_path"
        seen.add(path)
        content = item["content"]
        if not isinstance(content, str):
            return "build_file_content"
        size = len(content.encode("utf-8"))
        if size > MAX_BUILD_FILE_BYTES:
            return "build_file_size"
        total += size
        if total > MAX_BUILD_TOTAL_BYTES:
            return "build_total_size"
        searchable.append(content)
    joined = "\n".join(searchable)
    for required in required_text:
        if required not in joined:
            return "required_text_missing"
    return None


def check_build(value, ctx):
    """Mechanical bundle verifier. Passing does not establish code correctness."""
    error = validate_bundle(value, ctx.obligation.parameters.get("required_text", ()))
    if error:
        return Verdict.fail(error, "Return a bounded {summary, files:[{path, content}]} bundle. Files are review artifacts, not executed code.")
    return Verdict.passed()


def register_build(registry: Registry):
    register_common(registry)
    registry.check("workbench:build", check_build, "1")


def make_build_task(request: dict, root: Path):
    allowed = {"id", "prompt", "files", "mode", "model", "max_calls", "max_output_tokens", "required_text", "cloud_consent"}
    if not isinstance(request, dict) or set(request) - allowed:
        raise ContractError("unknown build mission fields")
    mid = request.get("id", "m-" + uuid.uuid4().hex)
    if not isinstance(mid, str) or not ID.fullmatch(mid):
        raise ContractError("invalid mission identity")
    prompt = request.get("prompt", "")
    if not isinstance(prompt, str) or not 1 <= len(prompt.encode("utf-8")) <= 4000 or not prompt.strip():
        raise ContractError("prompt must be nonempty and at most 4000 UTF-8 bytes")
    if request.get("mode", "build") != "build":
        raise ContractError("build runner only accepts build mode")
    if type(request.get("cloud_consent", False)) is not bool:
        raise ContractError("cloud consent must be boolean")
    required = request.get("required_text", [])
    if not isinstance(required, list) or len(required) > 8 or any(not isinstance(s, str) or not 1 <= len(s) <= 160 for s in required):
        raise ContractError("invalid acceptance strings")
    names = request.get("files", [])
    if not isinstance(names, list) or len(names) > 6 or len(set(names)) != len(names):
        raise ContractError("select zero to six distinct reference source files")
    artifacts, paths = source_snapshot(root, names) if names else ({}, {})
    consent = request.get("cloud_consent") is True
    artifacts = {key: dataclasses.replace(a, cloud=consent) for key, a in artifacts.items()}
    instruction = (prompt + "\n\nCreate a reviewable deliverable. Return exactly one value for obligation 'build' with "
                   "two fields: summary (short string) and files (one to eight objects with exactly path and content). "
                   "Paths must be relative text paths, never absolute, hidden, parent-relative, or duplicated. "
                   "For browser-facing apps or interactive web UI, return a directly previewable static bundle with an index.html entry point; "
                   "use only bundle-local JavaScript/CSS files or inline code, and do not require npm, a build step, a dev server, CDN assets, or remote network access. "
                   "Do not claim files were executed, tested, deployed, or merged. They will be written only into the mission artifact directory. "
                   "Reference source paths, if any: " + canonical(paths) +
                   "\nRequired literal text somewhere in the summary or generated files: " + canonical(required))
    obligation = Obligation("build", instruction, "workbench:build", tuple(artifacts),
                            parameters={"required_text": required, "paths": paths}, cloud=consent)
    calls, tokens = request.get("max_calls", 2), request.get("max_output_tokens", MAX_BUILD_OUTPUT_TOKENS)
    if type(calls) is not int or not 1 <= calls <= 3 or type(tokens) is not int or not 256 <= tokens <= MAX_BUILD_OUTPUT_TOKENS:
        raise ContractError("mission budget outside public workbench bounds")
    model = request.get("model", "gpt-5-nano")
    if not isinstance(model, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,95}", model):
        raise ContractError("invalid model identifier")
    limits = Limits(local_rounds=calls, expert_rounds=0, max_calls=calls, max_expert_calls=0,
                    max_request_bytes=60000, max_remote_input_bytes=120000,
                    max_output_tokens=tokens, seed_lines=12, max_requested_lines=100)
    return Task(mid, prompt, artifacts, (obligation,)), paths, model, limits


def write_bundle(folder: Path, value: dict):
    error = validate_bundle(value)
    if error:
        raise ContractError("accepted build bundle failed persistence validation")
    root = folder / "artifacts"
    root.mkdir(mode=0o700)
    manifest = []
    for item in value["files"]:
        rel = safe_artifact_path(item["path"])
        target = root.joinpath(*rel.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() or target.is_symlink():
            raise ContractError("artifact target unexpectedly exists")
        target.write_text(item["content"], encoding="utf-8")
        raw = item["content"].encode("utf-8")
        manifest.append({"path": str(rel), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
    save(root / "manifest.json", {"files": manifest, "executed": False,
                                  "scope": "Generated review artifacts only; not executed or applied to the repository."})
    return manifest


def execute_build(request: dict, *, root: Path, output_root: Path, mailbox: Path | None = None,
                  config: dict | None = None, observer=None):
    task, paths, model, limits = make_build_task(request, root)
    output_root.mkdir(parents=True, exist_ok=True)
    lock = output_root / ".active"
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.write(fd, task.id.encode()); os.close(fd)
    folder = output_root / task.id
    def emit(kind, data):
        if observer:
            observer({"mission_id": task.id, "kind": kind, "data": data})
    cancelled = lambda: mailbox is not None and (mailbox / f"{task.id}-cancel.json").exists()
    try:
        folder.mkdir()
        snapshot = {"id": task.id, "goal": task.goal,
                    "artifacts": [dataclasses.asdict(a) for a in task.artifacts.values()],
                    "obligations": [dataclasses.asdict(o) for o in task.obligations]}
        save(folder / "task.json", snapshot)
        save(folder / "request.json", {**request, "id": task.id, "mode": "build"})
        save(folder / "sources.json", paths)
        emit("mission_started", {"output": str(folder), "mode": "build", "limits": dataclasses.asdict(limits),
                                 "source_paths": paths, "semantic_verification": "UNKNOWN"})
        if config is not None:
            for name in ("local", "expert"):
                if config.get(name, {}).get("kind") == "demo":
                    raise ContractError("scripted providers are not permitted for build missions")
            config = {**config, "cache": {"enabled": False}, "limits": dataclasses.asdict(limits)}
            base = build_harness(config)
            register_build(base.source_registry)
            harness = ObservedHarness(base.source_registry, base.local, base.expert, limits=limits, cache=None)
        else:
            if mailbox is None or request.get("cloud_consent") is not True:
                raise ContractError("browser build missions require explicit cloud consent and a provider mailbox")
            registry = Registry(); register_build(registry)
            harness = ObservedHarness(registry, MailboxProvider(model, task.id, mailbox, emit, cancelled), None, limits=limits)
        harness.projected, harness.emit = 0, emit
        if isinstance(harness.local, MailboxProvider):
            delegate = harness.local.emit
            harness.local.emit = lambda kind, data: (harness.sync_events(), delegate(kind, data))[-1]
        result = harness.run(task); harness.sync_events()
        if any(c["usage"]["source"] == "simulation" for c in result["calls"]):
            raise ContractError("build mission received simulation usage")
        save(folder / "result.json", result); harness.ledger.write(folder / "trace.jsonl")
        result, proof = verify_run(folder); save(folder / "verification.json", proof)
        manifest = []
        if result["success"] and "build" in result["values"]:
            manifest = write_bundle(folder, result["values"]["build"])
        summary = {"output": str(folder), "status": result["status"], "simulation": False,
                   "execution": "generated_artifacts", "semantic_verification": "UNKNOWN",
                   "verification": proof, "result": result, "source_paths": paths, "task": snapshot,
                   "generated_files": manifest}
        save(folder / "summary.json", summary); emit("mission_finished", summary)
        return summary
    except BaseException:
        emit("mission_error", {"code": "mission_failed", "output": str(folder), "result_verified": False})
        raise
    finally:
        lock.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prompt", nargs="?")
    parser.add_argument("--request", type=Path)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output-root", type=Path, default=Path("runs/missions"))
    parser.add_argument("--mailbox", type=Path)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--allow-cloud", action="store_true")
    parser.add_argument("--files", nargs="*", default=[])
    parser.add_argument("--model", default="gpt-5-nano")
    parser.add_argument("--max-calls", type=int, default=2)
    parser.add_argument("--max-output-tokens", type=int, default=MAX_BUILD_OUTPUT_TOKENS)
    parser.add_argument("--stream", action="store_true")
    args = parser.parse_args(argv)
    if bool(args.request) == bool(args.prompt):
        parser.error("provide exactly one of prompt or --request")
    def stream(event):
        import base64
        from .runner import FRAME, MAX_RESULT
        raw = canonical(event).encode()
        if len(raw) > MAX_RESULT: raise ContractError("projection exceeds byte budget")
        print(FRAME + base64.urlsafe_b64encode(raw).decode() + "\x07", flush=True)
    try:
        request = read_json(args.request) if args.request else {
            "mode": "build", "prompt": args.prompt, "files": args.files, "model": args.model,
            "max_calls": args.max_calls, "max_output_tokens": args.max_output_tokens,
            "cloud_consent": args.allow_cloud}
        request["mode"] = "build"
        def deadline(_signum, _frame): raise WorkbenchDeadline("mission wall-clock budget exhausted")
        previous = signal.signal(signal.SIGALRM, deadline); signal.alarm(240)
        try:
            summary = execute_build(request, root=args.root, output_root=args.output_root,
                                    mailbox=args.mailbox,
                                    config=load_config(args.config) if args.config else None,
                                    observer=stream if args.stream else None)
        finally:
            signal.alarm(0); signal.signal(signal.SIGALRM, previous)
        print(canonical({"status": summary["status"], "output": summary["output"], "simulation": False,
                         "semantic_verification": "UNKNOWN", "generated_files": summary["generated_files"]}))
        return 0 if summary["result"]["success"] else 2
    except (ContractError, OSError, ValueError, TypeError, KeyError, TimeoutError, WorkbenchDeadline):
        print("Build mission failed: check provider consent, budget, artifact contract, or workspace lock. No success claimed.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
