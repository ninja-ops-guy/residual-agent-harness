"""Iterative generated-artifact workbench with explicit, verified lineage.

This extends the public Workbench build flow without granting repository or M4
execution authority. A follow-up build may reference one previous successful
build mission. The parent's result/trace/manifest/persisted bytes are rechecked,
then frozen as ordinary Harness evidence before the next provider call.
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import os
from pathlib import Path
import re
import signal
import sys
import uuid

from residual.config import build_harness, load_config
from residual.core import Artifact, ContractError, Obligation, Registry, Task, canonical
from residual.engine import Limits
from .build import register_build, validate_bundle, write_bundle
from .runner import (MailboxProvider, ObservedHarness, WorkbenchDeadline, read_json,
                     save, source_snapshot, verify_run)

MID = re.compile(r"m-[0-9a-f]{32}\Z")
CID = re.compile(r"c-[0-9a-f]{32}\Z")
MAX_PRIOR_TOTAL_BYTES = 80000


def _id(value, pattern, label, *, optional=False):
    if optional and value is None:
        return None
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise ContractError(f"invalid {label}")
    return value


def verified_parent_bundle(output_root: Path, parent_mission_id: str):
    """Return a persisted parent bundle only after every retained binding agrees."""
    parent_mission_id = _id(parent_mission_id, MID, "parent mission identity")
    root = output_root.resolve()
    folder = root / parent_mission_id
    if folder.is_symlink() or not folder.is_dir() or folder.resolve().parent != root:
        raise ContractError("parent mission is not a contained run directory")
    result, proof = verify_run(folder)
    if not proof.get("result_bound") or not result.get("success") or "build" not in result.get("values", {}):
        raise ContractError("parent mission is not a verified successful build")
    bundle = result["values"]["build"]
    if validate_bundle(bundle):
        raise ContractError("parent build bundle no longer satisfies the build contract")
    manifest = read_json(folder / "artifacts" / "manifest.json")
    if not isinstance(manifest, dict) or manifest.get("executed") is not False or not isinstance(manifest.get("files"), list):
        raise ContractError("parent artifact manifest is invalid")
    listed = {entry.get("path"): entry for entry in manifest["files"] if isinstance(entry, dict)}
    total = 0
    for item in bundle["files"]:
        path, content = item["path"], item["content"]
        meta = listed.get(path)
        if not meta:
            raise ContractError("parent artifact manifest does not cover the accepted bundle")
        target = folder / "artifacts" / path
        if target.is_symlink() or not target.is_file() or not target.resolve().is_relative_to((folder / "artifacts").resolve()):
            raise ContractError("parent artifact path is not a contained regular file")
        raw = target.read_bytes()
        encoded = content.encode("utf-8")
        total += len(encoded)
        if total > MAX_PRIOR_TOTAL_BYTES:
            raise ContractError("parent artifact bundle exceeds the continuation evidence budget")
        digest = hashlib.sha256(encoded).hexdigest()
        if raw != encoded or meta.get("bytes") != len(encoded) or meta.get("sha256") != digest:
            raise ContractError("parent artifact bytes do not match retained accepted evidence")
    summary_path = folder / "summary.json"
    revision = 1
    if summary_path.is_file() and not summary_path.is_symlink():
        try:
            summary = read_json(summary_path)
            revision = summary.get("lineage", {}).get("revision", 1)
            if type(revision) is not int or revision < 1:
                revision = 1
        except (OSError, ValueError, TypeError, KeyError):
            revision = 1
    return bundle, revision


def make_task(request: dict, root: Path, prior_bundle=None):
    allowed = {"id", "conversation_id", "parent_mission_id", "prompt", "files", "mode", "model",
               "max_calls", "max_output_tokens", "required_text", "cloud_consent"}
    if not isinstance(request, dict) or set(request) - allowed:
        raise ContractError("unknown iterative build mission fields")
    mid = _id(request.get("id", "m-" + uuid.uuid4().hex), MID, "mission identity")
    conversation_id = _id(request.get("conversation_id"), CID, "conversation identity", optional=True)
    parent_id = _id(request.get("parent_mission_id"), MID, "parent mission identity", optional=True)
    prompt = request.get("prompt", "")
    if not isinstance(prompt, str) or not 1 <= len(prompt.encode("utf-8")) <= 4000 or not prompt.strip():
        raise ContractError("prompt must be nonempty and at most 4000 UTF-8 bytes")
    if request.get("mode", "build") != "build":
        raise ContractError("iterative build runner only accepts build mode")
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
    artifacts = {key: dataclasses.replace(value, cloud=consent) for key, value in artifacts.items()}
    prior_paths = {}
    if prior_bundle is not None:
        if parent_id is None:
            raise ContractError("prior build evidence requires a parent mission identity")
        if validate_bundle(prior_bundle):
            raise ContractError("invalid prior build bundle")
        for index, item in enumerate(prior_bundle["files"]):
            key = f"prior-{index}"
            artifacts[key] = Artifact(key, item["content"], consent)
            prior_paths[key] = item["path"]
    instruction = prompt + "\n\n"
    if prior_paths:
        instruction += ("This is a revision of the immediately preceding accepted build. The frozen prior bundle is supplied as prior-* evidence. "
                        "Return the COMPLETE replacement deliverable, not a diff. Preserve unrelated working behavior unless the user explicitly asks to remove it. "
                        "Prior artifact paths: " + canonical(prior_paths) + "\n")
    instruction += ("Create a reviewable deliverable. Return exactly one value for obligation 'build' with two fields: summary (short string) and "
                    "files (one to eight objects with exactly path and content). Paths must be relative text paths, never absolute, hidden, parent-relative, or duplicated. "
                    "For browser-facing apps or interactive web UI, return a directly previewable static bundle with an index.html entry point; use only bundle-local "
                    "JavaScript/CSS files or inline code, and do not require npm, a build step, a dev server, CDN assets, or remote network access. "
                    "Do not claim files were executed, tested, deployed, or merged. They will be written only into the mission artifact directory. "
                    "Reference repository source paths, if any: " + canonical(paths) +
                    "\nRequired literal text somewhere in the summary or generated files: " + canonical(required))
    evidence = tuple(artifacts)
    obligation = Obligation("build", instruction, "workbench:build", evidence,
                            parameters={"required_text": required, "paths": paths, "prior_paths": prior_paths}, cloud=consent)
    calls, tokens = request.get("max_calls", 2), request.get("max_output_tokens", 1536)
    if type(calls) is not int or not 1 <= calls <= 3 or type(tokens) is not int or not 256 <= tokens <= 1536:
        raise ContractError("mission budget outside public workbench bounds")
    model = request.get("model", "gpt-5-nano")
    if not isinstance(model, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,95}", model):
        raise ContractError("invalid model identifier")
    limits = Limits(local_rounds=calls, expert_rounds=0, max_calls=calls, max_expert_calls=0,
                    max_request_bytes=60000, max_remote_input_bytes=120000,
                    max_output_tokens=tokens, seed_lines=12, max_requested_lines=100)
    return Task(mid, prompt, artifacts, (obligation,)), paths, model, limits, conversation_id, parent_id


def execute(request: dict, *, root: Path, output_root: Path, mailbox: Path | None = None,
            config: dict | None = None, observer=None):
    output_root.mkdir(parents=True, exist_ok=True)
    parent_id = request.get("parent_mission_id") if isinstance(request, dict) else None
    prior_bundle, parent_revision = (None, 0)
    if parent_id is not None:
        prior_bundle, parent_revision = verified_parent_bundle(output_root, parent_id)
    task, paths, model, limits, conversation_id, parent_id = make_task(request, root, prior_bundle)
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
        lineage = {"conversation_id": conversation_id, "parent_mission_id": parent_id,
                   "revision": parent_revision + 1 if parent_id else 1}
        emit("mission_started", {"output": str(folder), "mode": "build", "limits": dataclasses.asdict(limits),
                                 "source_paths": paths, "semantic_verification": "UNKNOWN", "lineage": lineage})
        if config is not None:
            for name in ("local", "expert"):
                if config.get(name, {}).get("kind") == "demo":
                    raise ContractError("scripted providers are not permitted for build missions")
            config = {**config, "cache": {"enabled": False}, "limits": dataclasses.asdict(limits)}
            base = build_harness(config); register_build(base.source_registry)
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
        if any(call["usage"]["source"] == "simulation" for call in result["calls"]):
            raise ContractError("build mission received simulation usage")
        save(folder / "result.json", result); harness.ledger.write(folder / "trace.jsonl")
        result, proof = verify_run(folder); save(folder / "verification.json", proof)
        manifest = []
        if result["success"] and "build" in result["values"]:
            manifest = write_bundle(folder, result["values"]["build"])
        summary = {"output": str(folder), "status": result["status"], "simulation": False,
                   "execution": "generated_artifacts", "semantic_verification": "UNKNOWN",
                   "verification": proof, "result": result, "source_paths": paths, "task": snapshot,
                   "generated_files": manifest, "lineage": lineage}
        save(folder / "summary.json", summary); emit("mission_finished", summary)
        return summary
    except BaseException:
        emit("mission_error", {"code": "mission_failed", "output": str(folder), "result_verified": False,
                               "lineage": {"conversation_id": conversation_id, "parent_mission_id": parent_id}})
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
    parser.add_argument("--max-output-tokens", type=int, default=1536)
    parser.add_argument("--conversation-id")
    parser.add_argument("--parent-mission-id")
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
            "cloud_consent": args.allow_cloud, "conversation_id": args.conversation_id,
            "parent_mission_id": args.parent_mission_id}
        request["mode"] = "build"
        def deadline(_signum, _frame): raise WorkbenchDeadline("mission wall-clock budget exhausted")
        previous = signal.signal(signal.SIGALRM, deadline); signal.alarm(240)
        try:
            summary = execute(request, root=args.root, output_root=args.output_root,
                              mailbox=args.mailbox,
                              config=load_config(args.config) if args.config else None,
                              observer=stream if args.stream else None)
        finally:
            signal.alarm(0); signal.signal(signal.SIGALRM, previous)
        print(canonical({"status": summary["status"], "output": summary["output"], "simulation": False,
                         "semantic_verification": "UNKNOWN", "generated_files": summary["generated_files"],
                         "lineage": summary["lineage"]}))
        return 0 if summary["result"]["success"] else 2
    except (ContractError, OSError, ValueError, TypeError, KeyError, TimeoutError, WorkbenchDeadline):
        print("Iterative build failed: check provider consent, parent evidence, budget, or workspace lock. No success claimed.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
