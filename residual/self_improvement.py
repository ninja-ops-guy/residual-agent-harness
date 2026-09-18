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
    "residual/eval_frozen/", "docs/self-improvement/generations/",
)
PROTECTED_EXACT = {
    "residual/goalspec.py", "residual/loop.py", "residual/receipts.py",
    "verifier/v3/factory_ownership_baseline.json",
    "docs/CURRENT_STATUS.md", "docs/roadmap/README.md", "docs/self-improvement/MISSION.md",
    "tests/test_self_improvement.py", "tests/__init__.py",
}
EXECUTABLE_CONFIG_NAMES = {
    "pyproject.toml", "package.json", "package-lock.json", "Dockerfile",
    "compose.yaml", "compose.yml", "docker-compose.yml", "Makefile",
    "pytest.ini", "tox.ini", "setup.cfg", "setup.py",
}
PROTECTED_BASENAMES = {"conftest.py", "sitecustomize.py", "usercustomize.py", "pytest.py"}
EXECUTABLE_SUFFIXES = {
    ".py", ".pyi", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx",
    ".sh", ".bash", ".zsh", ".fish", ".ps1", ".rb", ".go", ".rs",
    ".c", ".cc", ".cpp", ".h", ".hpp", ".java", ".kt", ".kts", ".cs",
    ".php", ".pl", ".lua", ".html", ".htm", ".vue", ".svelte", ".sql",
    ".css", ".scss",
}
CONFIG_SUFFIXES = {".json", ".toml", ".yaml", ".yml", ".ini", ".cfg"}
BLOCKING_HEALTH_CODES = {
    "roadmap_identity_missing", "roadmap_identity_unavailable",
    "current_status_identity_missing", "current_status_identity_unavailable",
    "roadmap_queue_missing", "required_path_missing",
}
REQUIRED = ("docs/roadmap/README.md", "docs/CURRENT_STATUS.md", "docs/self-improvement/MISSION.md",
            "residual/goalspec.py", "residual/loop.py", "residual/station/service.py",
            "residual/station/control.py", "tests/test_self_improvement.py",
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


def compare_recorded_main(root, recorded, main):
    if recorded is None:
        return "missing", None
    if not git(root, "rev-parse", "--verify", recorded + "^{commit}", allow_fail=True):
        return "unavailable", None
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "merge-base", "--is-ancestor", recorded, main],
            capture_output=True, text=True, timeout=15, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        raise ContractError("Git history could not be compared") from exc
    if result.returncode:
        return "diverged", None
    delta = int(git(root, "rev-list", "--count", recorded + ".." + main) or "0")
    return ("lag" if delta else "current"), delta


def append_snapshot_finding(findings, label, code_prefix, state, recorded, main, delta):
    if state == "missing":
        findings.append({"code": code_prefix + "_identity_missing", "severity": "warning",
                         "summary": label + " main snapshot is not parseable.", "evidence": {}})
    elif state == "unavailable":
        findings.append({"code": code_prefix + "_identity_unavailable", "severity": "warning",
                         "summary": label + " snapshot commit is unavailable.",
                         "evidence": {"recorded_main": recorded}})
    elif state == "diverged":
        findings.append({"code": code_prefix + "_identity_diverged", "severity": "error",
                         "summary": label + " recorded main is not an ancestor of repository main.",
                         "evidence": {"recorded_main": recorded, "main": main}})
    elif state == "lag":
        lag_code = code_prefix + ("_lag" if code_prefix.endswith("_status") else "_status_lag")
        findings.append({"code": lag_code, "severity": "warning",
                         "summary": label + " status snapshot trails repository main.",
                         "evidence": {"recorded_main": recorded, "main": main, "commits": delta}})


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
    current_status = root / "docs/CURRENT_STATUS.md"
    status_text = current_status.read_text(encoding="utf-8") if current_status.is_file() else ""
    status_match = ROADMAP_HEAD.search(status_text)
    status_recorded = status_match.group(1) if status_match else None
    findings = []
    missing = [p for p in REQUIRED if not (root / p).is_file()]
    if missing:
        findings.append({"code": "required_path_missing", "severity": "error",
                         "summary": "Required mission inputs are missing.", "evidence": {"paths": missing}})
    if dirty:
        findings.append({"code": "checkout_dirty", "severity": "warning",
                         "summary": "Checkout has uncommitted or untracked changes.", "evidence": {}})
    if not _is_ancestor(root, main, head):
        if _is_ancestor(root, head, main):
            source_main_state = "behind_main"
            findings.append({
                "code": "source_behind_main", "severity": "error",
                "summary": "The inspected source revision does not contain repository main.",
                "evidence": {"head": head, "main": main},
            })
        else:
            source_main_state = "diverged_from_main"
            findings.append({
                "code": "source_diverged_from_main", "severity": "error",
                "summary": "The inspected source revision has diverged from repository main.",
                "evidence": {"head": head, "main": main},
            })
    else:
        source_main_state = "contains_main"

    roadmap_state, delta = compare_recorded_main(root, recorded, main)
    append_snapshot_finding(findings, "Roadmap", "roadmap", roadmap_state, recorded, main, delta)
    status_state, status_delta = compare_recorded_main(root, status_recorded, main)
    append_snapshot_finding(
        findings, "Current status", "current_status", status_state, status_recorded, main, status_delta)
    queue = roadmap_items(text)
    if not queue:
        findings.append({"code": "roadmap_queue_missing", "severity": "warning",
                         "summary": "Current build order was not found.", "evidence": {}})
    inputs = {"roadmap_sha256": file_digest(roadmap),
              "current_status_sha256": file_digest(current_status),
              "mission_sha256": file_digest(root / "docs/self-improvement/MISSION.md"),
              "controller_sha256": file_digest(root / "residual/self_improvement.py"),
              "safety_regression_sha256": file_digest(root / "tests/test_self_improvement.py"),
              "factory_ownership_sha256": file_digest(root / "verifier/v3/factory_ownership_baseline.json")}
    report = {"schema_version": 1, "repository_root": str(root), "head": head, "main_head": main,
              "branch": branch, "dirty": dirty, "source_main_state": source_main_state,
              "roadmap_recorded_main": recorded,
              "roadmap_delta_commits": delta, "current_status_recorded_main": status_recorded,
              "current_status_delta_commits": status_delta,
              "roadmap_items": queue, "findings": findings,
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


def requires_frozen_command(path):
    p = Path(path)
    return (p.suffix.lower() in EXECUTABLE_SUFFIXES
            or p.name in EXECUTABLE_CONFIG_NAMES
            or (p.suffix.lower() in CONFIG_SUFFIXES and not path.startswith("docs/")))


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
    p = Path(path)
    return (path in PROTECTED_EXACT or path in ownership_paths
            or p.name in EXECUTABLE_CONFIG_NAMES or p.name in PROTECTED_BASENAMES
            or path.startswith("pytest/")
            or any(path.startswith(prefix) for prefix in PROTECTED_PREFIXES))


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


def governor_evaluator_checks(evaluator_files):
    checks = []
    for evaluator in evaluator_files:
        path = Path(evaluator)
        if not evaluator.startswith("tests/") or path.suffix.lower() != ".py" or not path.name.startswith("test_"):
            raise ContractError("Executable-code evaluators must be Python test files under tests/")
        checks.append({
            "kind": "command",
            "argv": ["{python}", "-I", "-c", "import os,sys; os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD']='1'; import pytest; sys.path.insert(0,'.'); raise SystemExit(pytest.main(['-q',sys.argv[1]]))", evaluator],
            "timeout": 120,
        })
    return checks


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
                or not isinstance(c["instruction"], str) or not isinstance(c["route"], str)
                or not c["files"] or not c["checks"] or c["route"] not in {"local", "cloud"}):
            raise ContractError("ImprovementCandidate is incomplete")
        if c["id"] in seen_ids:
            raise ContractError("ImprovementCandidate IDs must be unique")
        seen_ids.add(c["id"])
        if any(not isinstance(p, str) for p in c["files"] + c["context"] + c["evaluator_files"]):
            raise ContractError("Candidate paths must be strings")
        if any(not isinstance(dep, str) for dep in c["depends_on"]):
            raise ContractError("Candidate dependencies must be strings")
        for name in ("files", "context", "depends_on", "evaluator_files"):
            if len(set(c[name])) != len(c[name]):
                raise ContractError("Candidate path and dependency lists must be unique")
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
        if command_checks:
            raise ContractError("ImprovementCandidates may not author executable command checks")
        code_paths = [path for path in c["files"] if requires_frozen_command(path)]
        if code_paths and not c["evaluator_files"]:
            raise ContractError("Executable-code candidates require external frozen evaluator files")
        if not code_paths and c["evaluator_files"]:
            raise ContractError("Non-executable candidates must not declare executable evaluator files")
        derived_checks = governor_evaluator_checks(c["evaluator_files"]) if code_paths else []
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
                      "checks": c["checks"] + derived_checks, "route": c["route"]})
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



def planning_station_spec(report, plan, route="local", allow_executable=False):
    if route not in {"local", "cloud"}:
        raise ContractError("Planner route must be local or cloud")
    health_payload = json.dumps({
        "source_head": report["head"],
        "source_report_sha256": report["report_sha256"],
        "findings": report["findings"],
    }, ensure_ascii=False, allow_nan=False)
    roadmap_payload = json.dumps({
        "source_head": report["head"],
        "plan_sha256": plan["plan_sha256"],
        "queue": [item for item in plan["queue"] if item["source"] == "roadmap"],
    }, ensure_ascii=False, allow_nan=False)
    executable_policy = (
        "Executable-code candidates may be proposed only with at least one existing tests/test_*.py evaluator. "
        "Candidates MUST NOT author command checks; the Mission Governor derives executable pytest checks from evaluator_files after admission. "
        "Include deterministic non-command checks such as exists or python_compile as appropriate."
        if allow_executable else
        "Executable verification is not authorized for this generation. Propose only non-executable documentation/data changes; evaluator_files must be empty."
    )
    proposal_root = "docs/self-improvement/proposals/"
    health_file = proposal_root + "health.json"
    roadmap_file = proposal_root + "roadmap.json"
    candidate_file = proposal_root + "candidates.json"
    common_context = [
        "docs/self-improvement/MISSION.md",
        "docs/CURRENT_STATUS.md",
        "docs/roadmap/README.md",
        "residual/self_improvement.py",
        "residual/cli.py",
        "tests/test_self_improvement.py",
    ]
    tasks = [
        {
            "id": "SI_HEALTH_SCOUT",
            "title": "Health scout",
            "instruction": (
                "Analyze the certified Revision Doctor input below and the supplied repository context. "
                "Write a strict JSON research note to the declared file. Identify concrete self-healing or "
                "self-improvement opportunities, but do not claim permission to modify protected surfaces. "
                "Prefer small, testable, evidence-producing changes. Input: " + health_payload
            ),
            "depends_on": [],
            "files": [health_file],
            "context": common_context,
            "checks": [{"kind": "json_valid", "path": health_file}],
            "route": route,
        },
        {
            "id": "SI_ROADMAP_SCOUT",
            "title": "Roadmap scout",
            "instruction": (
                "Analyze the accepted roadmap queue and current-status evidence below. Write a strict JSON "
                "research note to the declared file. Separate accepted capability from research, FAIL, BLOCKED, "
                "and UNKNOWN evidence. Find bounded work that can advance the roadmap without crossing protected "
                "governance boundaries. Input: " + roadmap_payload
            ),
            "depends_on": [],
            "files": [roadmap_file],
            "context": common_context,
            "checks": [{"kind": "json_valid", "path": roadmap_file}],
            "route": route,
        },
        {
            "id": "SI_COMPOSER",
            "title": "Improvement candidate composer",
            "instruction": (
                "Synthesize the two scout reports into a strict JSON ImprovementCandidate manifest. "
                "Output exactly an object with schema_version=1 and candidates, with 1-4 candidates. Every "
                "candidate must contain exactly id,title,instruction,files,context,depends_on,checks,route,"
                "evaluator_files. Writable scopes must not overlap. Protected Factory, Station, verifier, "
                "workflow, swarm, evidence, scheduler, integrator, frozen-evaluation and ownership-manifest "
                "surfaces are out of scope. Current status, roadmap, M7 mission policy, M7 safety regression and "
                "generation-history files are also read-only authority inputs. " + executable_policy + " "
                "Documentation-only work may use deterministic exists/contains/json_valid checks. Use explicit dependencies if a "
                "candidate reads a file written by another candidate. Preserve historical FAIL/BLOCKED/UNKNOWN "
                "evidence and make no production-readiness claims. The deterministic Mission Governor will reject "
                "anything outside this contract. All candidate route values must be " + route + "."
            ),
            "depends_on": ["SI_HEALTH_SCOUT", "SI_ROADMAP_SCOUT"],
            "files": [candidate_file],
            "context": list(dict.fromkeys(common_context + [health_file, roadmap_file])),
            "checks": [{"kind": "json_valid", "path": candidate_file},
                       {"kind": "contains", "path": candidate_file, "text": '"candidates"'}],
            "route": route,
        },
    ]
    manifest = {
        "schema_version": 1,
        "name": "RESIDUAL self-improvement origination " + plan["generation"],
        "goal": ("Originate bounded self-improvement candidates from certified health and roadmap evidence. "
                 "Proposal generation has no implementation or promotion authority."),
        "tasks": tasks,
    }
    fence = chr(96) * 3
    markdown = "# RESIDUAL self-improvement origination\n\n" + fence + "json\n" + json.dumps(
        manifest, indent=2, ensure_ascii=False, allow_nan=False) + "\n" + fence + "\n"
    parse_spec(markdown)
    return markdown


def ready_report(repo):
    report = doctor_repository(repo)
    blocking = [
        finding for finding in report["findings"]
        if finding["severity"] == "error" or finding["code"] in BLOCKING_HEALTH_CODES
    ]
    if report["dirty"] or blocking:
        raise ContractError("Revision Doctor blocked generation execution")
    return report, mission_plan(report)


def assert_managed_source(station, pid, expected_head):
    managed_repo = Path(station.store.project(pid)["repo"]).resolve()
    managed_head = git(managed_repo, "rev-parse", "HEAD")
    if managed_head != expected_head:
        station.store.event(pid, "project.note", {
            "message": "Self-improvement generation blocked: managed clone source identity mismatch",
            "expected_head": expected_head, "managed_head": managed_head,
        })
        raise ContractError("Station managed clone does not match the certified source revision")
    return managed_repo


def originate_candidates(repo, station_data, route="local", allow_cloud=False, allow_command_checks=False):
    report, plan = ready_report(repo)
    if route == "cloud" and not allow_cloud:
        raise ContractError("Cloud origination requires explicit cloud permission")
    spec = planning_station_spec(report, plan, route, allow_executable=allow_command_checks)
    from residual.station.service import Station
    station = Station(station_data)
    pid = station.create(spec, source=report["repository_root"], allow_cloud=allow_cloud,
                         commands=False)["project_id"]
    managed_repo = assert_managed_source(station, pid, report["head"])
    batch = station.batch(pid)
    result = {
        "mission_id": MISSION_ID,
        "generation": plan["generation"],
        "source_head": report["head"],
        "source_report_sha256": report["report_sha256"],
        "plan_sha256": plan["plan_sha256"],
        "planner_spec_sha256": hashlib.sha256(spec.encode()).hexdigest(),
        "planner_project_id": pid,
        "planner_route": route,
        "planner_allows_executable": allow_command_checks,
        "batch": batch,
        "proposal": None,
        "proposal_sha256": None,
        "proposal_artifact": None,
        "export": None,
    }
    if batch["integrated"] != batch["total"] or batch.get("control", {}).get("outcome") != "success":
        return result
    proposal_path = managed_repo / "docs/self-improvement/proposals/candidates.json"
    try:
        raw = proposal_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ContractError("Planner completed without a readable candidate proposal") from exc
    artifact = station.store.add_artifact(pid, "PROPOSED-CANDIDATES.json", raw, "self-improvement-proposal")
    try:
        proposal = validate_candidate_doc(strict_json(raw))
        if any(candidate.get("route") != route for candidate in proposal["candidates"]):
            raise ContractError("Generated candidate routes must match the authorized planner route")
        if not allow_command_checks and any(
            requires_frozen_command(path)
            for candidate in proposal["candidates"] for path in candidate.get("files", [])
        ):
            raise ContractError("Generated executable candidates require explicit command-check permission")
        build_station_spec(report, plan, proposal, report["repository_root"])
    except (ContractError, ValueError, TypeError, KeyError):
        station.store.event(pid, "project.note", {
            "message": "Generated candidate proposal failed deterministic Mission Governor admission",
            "evidence": artifact["id"],
        })
        raise
    proposal_sha = digest(proposal)
    station.store.event(pid, "project.note", {
        "message": "Generated candidate proposal passed deterministic Mission Governor admission",
        "evidence": artifact["id"], "candidate_sha256": proposal_sha,
    })
    result.update(proposal=proposal, proposal_sha256=proposal_sha,
                  proposal_artifact=artifact, export=station.export(pid))
    return result


def execute_candidate_doc(report, plan, candidate_doc, station_data,
                          allow_cloud=False, allow_command_checks=False):
    candidate_doc = validate_candidate_doc(candidate_doc)
    spec = build_station_spec(report, plan, candidate_doc, report["repository_root"])
    if not allow_command_checks and any(
        requires_frozen_command(path)
        for candidate in candidate_doc["candidates"] for path in candidate["files"]
    ):
        raise ContractError("Executable self-improvement requires explicit command-check permission")
    from residual.station.service import Station
    station = Station(station_data)
    source_tree = git(report["repository_root"], "rev-parse", report["head"] + "^{tree}")
    pid = station.create(spec, source=report["repository_root"], allow_cloud=allow_cloud,
                         commands=allow_command_checks)["project_id"]
    managed_repo = assert_managed_source(station, pid, report["head"])
    batch = station.batch(pid)
    successor_head = git(managed_repo, "rev-parse", "HEAD")
    successor_tree = git(managed_repo, "rev-parse", successor_head + "^{tree}")
    meaningful_delta = successor_tree != source_tree
    completed = batch["integrated"] == batch["total"] and batch.get("control", {}).get("outcome") == "success"
    accepted_successor = completed and meaningful_delta
    export = None
    if completed and not meaningful_delta:
        station.store.event(pid, "project.note", {
            "message": "Self-improvement generation completed without a tree delta; successor promotion withheld",
            "source_tree": source_tree, "successor_tree": successor_tree,
        })
    if accepted_successor:
        export = station.export(pid)
    return {
        "mission_id": MISSION_ID,
        "generation": plan["generation"],
        "source_head": report["head"],
        "source_tree": source_tree,
        "source_report_sha256": report["report_sha256"],
        "plan_sha256": plan["plan_sha256"],
        "candidate_manifest_sha256": digest(candidate_doc),
        "station_spec_sha256": hashlib.sha256(spec.encode()).hexdigest(),
        "project_id": pid,
        "batch": batch,
        "successor_head": successor_head,
        "successor_tree": successor_tree,
        "successor_repo": str(managed_repo),
        "meaningful_delta": meaningful_delta,
        "accepted_successor": accepted_successor,
        "export": export,
    }


def run_cycle(repo, station_data, route="local", allow_cloud=False, allow_command_checks=False):
    origin = originate_candidates(
        repo, station_data, route=route, allow_cloud=allow_cloud,
        allow_command_checks=allow_command_checks)
    if origin["proposal"] is None:
        return {"mission_id": MISSION_ID, "generation": origin["generation"],
                "origin": origin, "execution": None}
    report, plan = ready_report(repo)
    if (report["head"] != origin["source_head"]
            or report["report_sha256"] != origin["source_report_sha256"]
            or plan["plan_sha256"] != origin["plan_sha256"]):
        raise ContractError("Source evidence changed between origination and execution")
    execution = execute_candidate_doc(
        report, plan, origin["proposal"], station_data,
        allow_cloud=allow_cloud, allow_command_checks=allow_command_checks)
    return {"mission_id": MISSION_ID, "generation": plan["generation"],
            "origin": origin, "execution": execution}


def run_lineage(repo, station_data, generations=3, route="local",
                allow_cloud=False, allow_command_checks=False):
    if type(generations) is not int or not 1 <= generations <= 10:
        raise ContractError("Experimental lineage must contain 1-10 bounded generations")
    governor_sha256 = file_digest(Path(__file__))
    current_source = str(Path(repo).resolve())
    history = []
    stop_reason = "max_generations"
    for ordinal in range(1, generations + 1):
        cycle = run_cycle(
            current_source, station_data, route=route, allow_cloud=allow_cloud,
            allow_command_checks=allow_command_checks)
        origin = cycle["origin"]
        execution = cycle["execution"]
        entry = {
            "ordinal": ordinal,
            "generation": cycle["generation"],
            "source_repo": current_source,
            "source_head": origin["source_head"],
            "source_report_sha256": origin["source_report_sha256"],
            "plan_sha256": origin["plan_sha256"],
            "planner_project_id": origin["planner_project_id"],
            "proposal_sha256": origin["proposal_sha256"],
            "execution_project_id": execution["project_id"] if execution else None,
            "accepted_successor": bool(execution and execution.get("accepted_successor")),
            "successor_head": execution.get("successor_head") if execution else None,
            "successor_tree": execution.get("successor_tree") if execution else None,
            "export": execution.get("export") if execution else None,
        }
        history.append(entry)
        if execution is None:
            stop_reason = "origination_incomplete"
            break
        if not execution.get("accepted_successor"):
            stop_reason = "execution_incomplete_or_no_delta"
            break
        successor_repo = execution.get("successor_repo")
        if not successor_repo or Path(successor_repo).resolve() == Path(current_source).resolve():
            raise ContractError("Experimental lineage successor source is invalid")
        current_source = successor_repo
    return {
        "mission_id": MISSION_ID,
        "mode": "experimental_lineage",
        "governor_sha256": governor_sha256,
        "requested_generations": generations,
        "attempted_generations": len(history),
        "accepted_generations": sum(1 for item in history if item["accepted_successor"]),
        "stop_reason": stop_reason,
        "initial_source_repo": str(Path(repo).resolve()),
        "final_candidate_repo": current_source,
        "history": history,
    }


def execute_generation(repo, candidates, station_data, allow_cloud=False, allow_command_checks=False):
    report, plan = ready_report(repo)
    return execute_candidate_doc(
        report, plan, load_candidates(candidates), station_data,
        allow_cloud=allow_cloud, allow_command_checks=allow_command_checks)


def revision_main(argv=None):
    p = argparse.ArgumentParser(prog="residual revision")
    sub = p.add_subparsers(dest="command", required=True)
    d = sub.add_parser("doctor")
    d.add_argument("--repo", default=".")
    d.add_argument("--json", action="store_true")
    d.add_argument("--strict", action="store_true")
    d.add_argument("--improve", action="store_true")
    d.add_argument("--station-data", default=".residual/self-improve")
    d.add_argument("--generations", type=int, default=1)
    d.add_argument("--route", choices=["local", "cloud"], default="local")
    d.add_argument("--allow-cloud", action="store_true")
    d.add_argument("--allow-command-checks", action="store_true")
    args = p.parse_args(argv)
    try:
        if args.improve:
            result = run_lineage(
                args.repo, args.station_data, generations=args.generations, route=args.route,
                allow_cloud=args.allow_cloud, allow_command_checks=args.allow_command_checks)
            print(json.dumps(result, indent=2))
            history = result["history"]
            return 0 if history and history[-1]["accepted_successor"] else 2
        report = doctor_repository(args.repo)
        print(canonical(report) if args.json else json.dumps(report, indent=2))
        return 2 if args.strict and report["findings"] else 0
    except (ContractError, OSError, ValueError, TypeError, KeyError):
        message = ("improvement generation could not be validated or executed"
                   if getattr(args, "improve", False)
                   else "repository health could not be validated")
        print("residual revision: " + message, file=sys.stderr)
        return 1


def self_improve_main(argv=None):
    p = argparse.ArgumentParser(prog="residual self-improve")
    sub = p.add_subparsers(dest="command", required=True)
    plan = sub.add_parser("plan")
    plan.add_argument("--repo", default=".")
    plan.add_argument("--candidates")
    originate = sub.add_parser("originate")
    originate.add_argument("--repo", default=".")
    originate.add_argument("--station-data", required=True)
    originate.add_argument("--route", choices=["local", "cloud"], default="local")
    originate.add_argument("--allow-cloud", action="store_true")
    originate.add_argument("--allow-command-checks", action="store_true")
    run = sub.add_parser("run")
    run.add_argument("--repo", default=".")
    run.add_argument("--candidates", required=True)
    run.add_argument("--station-data", required=True)
    run.add_argument("--allow-cloud", action="store_true")
    run.add_argument("--allow-command-checks", action="store_true")
    cycle = sub.add_parser("cycle")
    cycle.add_argument("--repo", default=".")
    cycle.add_argument("--station-data", required=True)
    cycle.add_argument("--route", choices=["local", "cloud"], default="local")
    cycle.add_argument("--allow-cloud", action="store_true")
    cycle.add_argument("--allow-command-checks", action="store_true")
    lineage = sub.add_parser("lineage")
    lineage.add_argument("--repo", default=".")
    lineage.add_argument("--station-data", required=True)
    lineage.add_argument("--generations", type=int, default=3)
    lineage.add_argument("--route", choices=["local", "cloud"], default="local")
    lineage.add_argument("--allow-cloud", action="store_true")
    lineage.add_argument("--allow-command-checks", action="store_true")
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
        if args.command == "originate":
            result = originate_candidates(
                args.repo, args.station_data, route=args.route, allow_cloud=args.allow_cloud,
                allow_command_checks=args.allow_command_checks)
            print(json.dumps(result, indent=2))
            control = result["batch"].get("control", {})
            return 0 if result["proposal"] is not None and control.get("outcome") == "success" else 2
        if args.command == "cycle":
            result = run_cycle(
                args.repo, args.station_data, route=args.route, allow_cloud=args.allow_cloud,
                allow_command_checks=args.allow_command_checks)
            print(json.dumps(result, indent=2))
            execution = result["execution"]
            if execution is None:
                return 2
            return 0 if execution.get("accepted_successor") else 2
        if args.command == "lineage":
            result = run_lineage(
                args.repo, args.station_data, generations=args.generations, route=args.route,
                allow_cloud=args.allow_cloud, allow_command_checks=args.allow_command_checks)
            print(json.dumps(result, indent=2))
            history = result["history"]
            return 0 if history and history[-1]["accepted_successor"] else 2
        result = execute_generation(args.repo, args.candidates, args.station_data,
                                    args.allow_cloud, args.allow_command_checks)
        print(json.dumps(result, indent=2))
        return 0 if result.get("accepted_successor") else 2
    except (ContractError, OSError, ValueError, TypeError, KeyError):
        print("residual self-improve: generation could not be validated or executed", file=sys.stderr)
        return 1
