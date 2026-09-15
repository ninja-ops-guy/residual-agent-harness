#!/usr/bin/env python3
"""Six inert application fixtures through real Factory plans and contracts.

This is a development demonstration, not a model benchmark or an integration
authority. Candidate programs, patches, commands and tests are never executed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from residual.core import digest, strict_json
from residual.factory.compiler import RequirementCompiler
from residual.factory.worker_contract import WorkerContract


def load_cases(root: Path) -> list[dict]:
    manifest = strict_json((root / "manifest.json").read_text())
    if manifest.get("schema_version") != "residual.application-fixtures.v1":
        raise ValueError("unsupported application fixture manifest")
    cases = []
    seen = set()
    for item in manifest["cases"]:
        name = item["file"]
        if not isinstance(name, str) or Path(name).name != name or not name.endswith(".json"):
            raise ValueError("fixture filename must be a plain JSON basename")
        path = root / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("fixture must be a regular file")
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != item["sha256"]:
            raise ValueError("application fixture hash mismatch")
        case = strict_json(raw.decode())
        if case["id"] in seen:
            raise ValueError("duplicate fixture id")
        seen.add(case["id"])
        cases.append(case)
    return cases


def assess(case: dict, candidate: object) -> str:
    """Closed-world fixture oracle; no arbitrary code evaluation or IO."""
    if candidate is None:
        return "UNKNOWN"
    if not isinstance(candidate, dict):
        return "FAIL"
    # These fixture-specific expected values are independently authored. The
    # oracle is intentionally narrow: it demonstrates rejection and abstention,
    # not general semantic verification of programs or security analysis.
    return "PASS" if candidate == case["expected"] else "FAIL"


def prepare_case(case: dict, commit: str) -> dict:
    plan = RequirementCompiler().compile(case["intent_document"]).plan
    if plan is None:
        raise ValueError("fixture did not compile into a complete plan")
    plan_hash = plan.graph_hash
    contracts = []
    requirements = {r.id: r for r in plan.requirements}
    for index, task in enumerate(plan.tasks):
        contract = WorkerContract(
            task_id=task.id, worker_id=f"fixture-worker-{index}",
            swarm_id="application-preflight", execution_plan_hash=plan_hash,
            attempt_id=f"fixture-attempt-{index}", lease_id=f"fixture-lease-{index}",
            lease_generation=1, input_commit=commit,
            workspace_root="/application-preflight", inputs=("input.json",),
            allowed_outputs=("candidate.json",), forbidden=("secrets/",),
            requirements=task.requirement_ids,
            acceptance=tuple(c for r in task.requirement_ids for c in requirements[r].acceptance),
            dependencies=task.depends_on, allowed_tools=(), forbidden_tools=("shell",),
            token_budget=0, wall_clock_budget_s=1, max_tool_calls=0,
            max_file_writes=1, memory_limit_mb=64,
            engine_hint="inert-scripted-fixture", engine_class="local",
        )
        contract.assert_matches_plan(plan)
        contracts.append({"contract": contract.to_dict(), "contract_hash": contract.contract_hash})
    outcomes = {variant: assess(case, case["candidates"][variant])
                for variant in ("good", "broken", "missing")}
    if outcomes != {"good": "PASS", "broken": "FAIL", "missing": "UNKNOWN"}:
        raise ValueError("fixture controls do not match independent labels")
    if plan.graph_hash != plan_hash:
        raise ValueError("plan mutated during contract preparation")
    return {
        "application": case["id"], "plan": plan.to_dict(),
        "contracts": contracts, "candidate_assessments": outcomes,
        "candidate_hashes": {k: digest(v) for k, v in case["candidates"].items()},
        "input_hash": digest(case["input"]),
        "station_acceptance": "NOT_REQUESTED", "integration_receipt": None,
    }


def run(cases_dir: Path, commit: str) -> dict:
    result = {
        "schema_version": "residual.application-preflight-report.v1",
        "evidence_level": "development_fixture", "confirmatory_eligible": False,
        "input_commit": commit, "model_calls": 0,
        "exercised": ["RequirementCompiler", "ExecutionPlan", "WorkerContract",
                      "fixture-only independent assessment"],
        "not_exercised": ["live model", "M2 OS execution", "M3 receipt publication",
                          "M4 sandbox/integration", "deployment"],
        "applications": [prepare_case(c, commit) for c in load_cases(cases_dir)],
    }
    result["report_hash"] = digest(result)
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=ROOT / "examples/application-preflight")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        report = run(args.cases, commit)
        text = json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("x", encoding="utf-8") as stream:
                stream.write(text)
        else:
            print(text, end="")
        return 0
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError):
        print("application-preflight: fixture validation failed", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
