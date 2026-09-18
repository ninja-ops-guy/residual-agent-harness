"""Governed recursive self-improvement planning and Station execution."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

from residual.core import ContractError, canonical, strict_json
from residual.station.contracts import parse_spec, path_ok

MISSION_ID = "residual-self-improvement"
ROADMAP_HEAD = re.compile("Current " + chr(96) + r"main" + chr(96) + r" is \*\*" + chr(96) + r"([0-9a-f]{40})" + chr(96) + r"\*\*\.")
PROTECTED_PREFIXES = (
    ".github/workflows/", "residual/factory/", "residual/station/", "verifier/",
    "residual/swarm/", "residual/evidence/", "residual/scheduler/", "residual/integrator/",
    "residual/eval_frozen/",
)
PROTECTED_EXACT = {"residual/goalspec.py", "residual/loop.py", "residual/receipts.py",
                   "verifier/v3/factory_ownership_baseline.json"}
REQUIRED = ("docs/roadmap/README.md", "docs/CURRENT_STATUS.md", "residual/goalspec.py",
            "residual/loop.py", "residual/station/service.py", "residual/station/control.py",
            "verifier/v3/factory_ownership_baseline.json")


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def file_digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def git(repo, *args, allow_fail=False):
    try:
        p = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                           timeout=15, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        raise ContractError("Git state could not be inspected") from exc
    if p.returncode and not allow_fail:
        raise ContractError("Git state could not be inspected")
    return p.stdout.strip() if p.returncode == 0 else ""


def main_head(repo, fallback):
    for ref in ("refs/heads/main", "refs/remotes/origin/main"):
        value = git(repo, "rev-parse", "--verify", ref, allow_fail=True)
        if re.fullmatch(r"[0-9a-f]{40}", value):
            return value
    return fallback


def roadmap_items(text):
    marker = "## Current build order"
    if marker not in text:
        return []
    section = text.split(marker, 1)[1].split("\n## ", 1)[0]
    out = []
    for line in section.splitlines():
        m = re.match(r"^\s*(\d+)\.\s+(.*\S)\s*$", line)
        if m:
            out.append({"position": int(m.group(1)), "text": m.group(2)})
    return out


def doctor_repository(repo="."):
    requested = Path(repo).resolve()
    if not requested.is_dir():
        raise ContractError("Repository path does not exist")
    root = Path(git(requested, "rev-parse", "--show-toplevel")).resolve()
    head = git(root, "rev-parse", "HEAD")
    branch = git(root, "branch", "--show-current") or "(detached)"
    main = main_head(root, head)
    dirty = bool(git(root, "status", "--porcelain=v1", "--untracked-files=all"))
    roadmap = root / "docs/roadmap/README.md"
    text = roadmap.read_text(encoding="utf-8") if roadmap.is_file() else ""
    match = ROADMAP_HEAD.search(text)
    recorded = match.group(1) if match else None
    findings = []
    missing = [p for p in REQUIRED if not (root / p).is_file()]
    if missing:
        findings.append({"code": "required_path_missing", "severity": "error",
                         "summary": "Required mission inputs are missing.", "evidence": {"paths": missing}})
    if dirty:
        findings.append({"code": "checkout_dirty", "severity": "warning",
                         "summary": "Checkout has uncommitted or untracked changes.", "evidence": {}})
    delta = None
    if recorded is None:
        findings.append({"code": "roadmap_identity_missing", "severity": "warning",
                         "summary": "Roadmap accepted-main snapshot is not parseable.", "evidence": {}})
    elif not git(root, "rev-parse", "--verify", recorded + "^{commit}", allow_fail=True):
        findings.append({"code": "roadmap_identity_unavailable", "severity": "warning",
                         "summary": "Roadmap snapshot commit is unavailable.", "evidence": {"roadmap_main": recorded}})
    else:
        ancestor = subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor", recorded, main],
                                  capture_output=True, timeout=15, check=False)
        if ancestor.returncode:
            findings.append({"code": "roadmap_identity_diverged", "severity": "error",
                             "summary": "Roadmap snapshot is not an ancestor of main.",
                             "evidence": {"roadmap_main": recorded, "main": main}})
        else:
            delta = int(git(root, "rev-list", "--count", recorded + ".." + main) or "0")
            if delta:
                findings.append({"code": "roadmap_status_lag", "severity": "warning",
                                 "summary": "Roadmap status snapshot trails main.",
                                 "evidence": {"roadmap_main": recorded, "main": main, "commits": delta}})
    queue = roadmap_items(text)
    if not queue:
        findings.append({"code": "roadmap_queue_missing", "severity": "warning",
                         "summary": "Current build order was not found.", "evidence": {}})
    inputs = {"roadmap_sha256": file_digest(roadmap),
              "current_status_sha256": file_digest(root / "docs/CURRENT_STATUS.md"),
              "mission_sha256": file_digest(root / "docs/self-improvement/MISSION.md")}
    report = {"schema_version": 1, "repository_root": str(root), "head": head, "main_head": main,
              "branch": branch, "dirty": dirty, "roadmap_recorded_main": recorded,
              "roadmap_delta_commits": delta, "roadmap_items": queue, "findings": findings,
              "inputs": inputs}
    report["report_sha256"] = digest({k: v for k, v in report.items() if k != "repository_root"})
    return report


def mission_plan(report):
    queue = [{"source": "revision_doctor", "id": f["code"],
              "priority": "P0" if f["severity"] == "error" else "P1", "summary": f["summary"]}
             for f in report["findings"]]
    queue.extend({"source": "roadmap", "id": "roadmap-%02d" % i["position"],
                  "priority": "P%d" % min(i["position"], 9), "summary": i["text"]}
                 for i in report["roadmap_items"])
    plan = {"schema_version": 1, "mission_id": MISSION_ID, "source_head": report["head"],
            "source_report_sha256": report["report_sha256"], "generation": report["report_sha256"][:12],
            "hierarchy": {"mission_governor": ["health_director", "roadmap_director", "swarm_director"],
                          "health_director": ["revision_doctor"],
                          "roadmap_director": ["scout", "research"],
                          "swarm_director": ["implementation", "critic", "verifier", "integrator"]},
            "authority": {"inspect": "autonomous", "plan": "autonomous",
                          "managed_implementation": "validated_unprotected_candidates",
                          "protected_paths": "external_governance_required",
                          "production_merge": "external_governed_authority"},
            "queue": queue}
    plan["plan_sha256"] = digest(plan)
    return plan


def factory_protected_paths(root):
    baseline = Path(root) / "verifier/v3/factory_ownership_baseline.json"
    try:
        value = strict_json(baseline.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ContractError("Factory ownership baseline could not be read") from exc
    if not isinstance(value, dict) or not isinstance(value.get("files"), dict) or not value["files"]:
        raise ContractError("Factory ownership baseline is invalid")
    paths = set()
    for path, blob in value["files"].items():
        if not isinstance(path, str) or not isinstance(blob, str) or not re.fullmatch(r"[0-9a-f]{40}", blob):
            raise ContractError("Factory ownership baseline contains an invalid file pin")
        path_ok(path)
        paths.add(path)
    return frozenset(paths)


def protected(path, ownership_paths=()):
    return (path in PROTECTED_EXACT or path in ownership_paths
            or any(path.startswith(p) for p in PROTECTED_PREFIXES))


def validate_candidate_doc(value):
    if not isinstance(value, dict) or set(value) != {"schema_version", "candidates"}:
        raise ContractError("Candidate manifest fields are invalid")
    candidates = value.get("candidates")
    if value.get("schema_version") != 1 or not isinstance(candidates, list) or not 1 <= len(candidates) <= 12:
        raise ContractError("Candidate manifest schema is invalid")
    return value


def load_candidates(path):
    try:
        value = strict_json(Path(path).read_text(encoding="utf-8"))
    except OSError as exc:
        raise ContractError("Candidate manifest could not be read") from exc
    return validate_candidate_doc(value)


def build_station_spec(report, plan, doc, repo):
    root = Path(repo).resolve()
    tasks = []
    allowed = {"id", "title", "instruction", "files", "context", "depends_on", "checks", "route", "evaluator_files"}
    ownership_paths = factory_protected_paths(root)
    write_owners = {}
    evaluator_paths = set()
    candidate_meta = {}
    seen_ids = set()
    for c in doc["candidates"]:
        if not isinstance(c, dict) or set(c) != allowed:
            raise ContractError("ImprovementCandidate fields are invalid")
        for name in ("files", "context", "depends_on", "checks", "evaluator_files"):
            if not isinstance(c[name], list):
                raise ContractError("ImprovementCandidate collections must be lists")
        if (not isinstance(c["id"], str) or not isinstance(c["title"], str)
                or not isinstance(c["instruction"], str) or not c["files"] or not c["checks"]
                or c["route"] not in {"local", "cloud"}):
            raise ContractError("ImprovementCandidate is incomplete")
        if c["id"] in seen_ids:
            raise ContractError("ImprovementCandidate IDs must be unique")
        seen_ids.add(c["id"])
        if any(not isinstance(p, str) for p in c["files"] + c["context"] + c["evaluator_files"]):
            raise ContractError("Candidate paths must be strings")
        if any(not isinstance(dep, str) for dep in c["depends_on"]):
            raise ContractError("Candidate dependencies must be strings")
        if set(c["files"]) & set(c["evaluator_files"]):
            raise ContractError("Candidate cannot modify its own evaluator")
        for path in c["files"] + c["context"] + c["evaluator_files"]:
            path_ok(path)
        protected_files = sorted(path for path in c["files"] if protected(path, ownership_paths))
        if protected_files:
            raise ContractError("Protected path requires external governance")
        missing_evaluators = sorted(path for path in c["evaluator_files"] if not (root / path).is_file())
        if missing_evaluators:
            raise ContractError("Frozen evaluator file is missing")
        command_checks = [check for check in c["checks"]
                          if isinstance(check, dict) and check.get("kind") == "command"]
        code_paths = [path for path in c["files"]
                      if Path(path).suffix.lower() in {".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".sh", ".ps1"}]
        if command_checks and not c["evaluator_files"]:
            raise ContractError("Command checks require external frozen evaluator files")
        if code_paths and (not command_checks or not c["evaluator_files"]):
            raise ContractError("Executable-code candidates require command checks and external frozen evaluator files")
        for path in c["files"]:
            if path in write_owners:
                raise ContractError("Candidate writable scopes must not overlap")
            write_owners[path] = c["id"]
        evaluator_paths.update(c["evaluator_files"])
        candidate_meta[c["id"]] = (tuple(c["context"]), frozenset(c["depends_on"]))
        instruction = c["instruction"] + (
            "\n\nGeneration rules: modify only writable files; evaluator files and checks are immutable; "
            "preserve historical FAIL/BLOCKED/UNKNOWN evidence.")
        tasks.append({"id": c["id"], "title": c["title"], "instruction": instruction,
                      "depends_on": c["depends_on"], "files": c["files"],
                      "context": list(dict.fromkeys(c["context"] + c["evaluator_files"])),
                      "checks": c["checks"], "route": c["route"]})
    if set(write_owners) & evaluator_paths:
        raise ContractError("Generation evaluator files must remain immutable across all candidates")
    for candidate_id, (context, dependencies) in candidate_meta.items():
        for path in context:
            owner = write_owners.get(path)
            if owner and owner != candidate_id and owner not in dependencies:
                raise ContractError("Generated-file context requires an explicit dependency on its writer")
    manifest = {"schema_version": 1, "name": "RESIDUAL self-improvement " + plan["generation"],
                "goal": "Improve RESIDUAL from " + report["head"] + " without crossing frozen evaluation or trust boundaries.",
                "tasks": tasks}
    fence = chr(96) * 3
    markdown = "# RESIDUAL self-improvement generation\n\n" + fence + "json\n" + json.dumps(manifest, indent=2) + "\n" + fence + "\n"
    parse_spec(markdown)
    return markdown


def execute_generation(repo, candidates, station_data, allow_cloud=False, allow_command_checks=False):
    report = doctor_repository(repo)
    if report["dirty"] or any(f["severity"] == "error" for f in report["findings"]):
        raise ContractError("Revision Doctor blocked generation execution")
    plan = mission_plan(report)
    spec = build_station_spec(report, plan, load_candidates(candidates), report["repository_root"])
    from residual.station.service import Station
    station = Station(station_data)
    pid = station.create(spec, source=report["repository_root"], allow_cloud=allow_cloud,
                         commands=allow_command_checks)["project_id"]
    managed_repo = Path(station.store.project(pid)["repo"]).resolve()
    managed_head = git(managed_repo, "rev-parse", "HEAD")
    if managed_head != report["head"]:
        station.store.event(pid, "project.note", {
            "message": "Self-improvement generation blocked: managed clone source identity mismatch",
            "expected_head": report["head"], "managed_head": managed_head,
        })
        raise ContractError("Station managed clone does not match the certified source revision")
    batch = station.batch(pid)
    export = None
    if batch["integrated"] == batch["total"] and batch.get("control", {}).get("outcome") == "success":
        export = station.export(pid)
    return {"mission_id": MISSION_ID, "generation": plan["generation"],
            "source_head": report["head"], "source_report_sha256": report["report_sha256"],
            "plan_sha256": plan["plan_sha256"], "project_id": pid, "batch": batch, "export": export}


def revision_main(argv=None):
    p = argparse.ArgumentParser(prog="residual revision")
    sub = p.add_subparsers(dest="command", required=True)
    d = sub.add_parser("doctor")
    d.add_argument("--repo", default=".")
    d.add_argument("--json", action="store_true")
    d.add_argument("--strict", action="store_true")
    args = p.parse_args(argv)
    try:
        report = doctor_repository(args.repo)
        print(canonical(report) if args.json else json.dumps(report, indent=2))
        return 2 if args.strict and report["findings"] else 0
    except (ContractError, OSError, ValueError, TypeError, KeyError):
        print("residual revision: repository health could not be validated", file=sys.stderr)
        return 1


def self_improve_main(argv=None):
    p = argparse.ArgumentParser(prog="residual self-improve")
    sub = p.add_subparsers(dest="command", required=True)
    plan = sub.add_parser("plan")
    plan.add_argument("--repo", default=".")
    plan.add_argument("--candidates")
    run = sub.add_parser("run")
    run.add_argument("--repo", default=".")
    run.add_argument("--candidates", required=True)
    run.add_argument("--station-data", required=True)
    run.add_argument("--allow-cloud", action="store_true")
    run.add_argument("--allow-command-checks", action="store_true")
    args = p.parse_args(argv)
    try:
        if args.command == "plan":
            report = doctor_repository(args.repo)
            payload = {"doctor": report, "mission": mission_plan(report)}
            if args.candidates:
                doc = load_candidates(args.candidates)
                spec = build_station_spec(report, payload["mission"], doc, report["repository_root"])
                payload["candidate_manifest_sha256"] = digest(doc)
                payload["station_spec_sha256"] = hashlib.sha256(spec.encode()).hexdigest()
                payload["station_spec"] = spec
            print(json.dumps(payload, indent=2))
            return 0
        result = execute_generation(args.repo, args.candidates, args.station_data,
                                    args.allow_cloud, args.allow_command_checks)
        print(json.dumps(result, indent=2))
        control = result["batch"].get("control", {})
        return 0 if result["batch"]["integrated"] == result["batch"]["total"] and control.get("outcome") == "success" else 2
    except (ContractError, OSError, ValueError, TypeError, KeyError):
        print("residual self-improve: generation could not be validated or executed", file=sys.stderr)
        return 1
