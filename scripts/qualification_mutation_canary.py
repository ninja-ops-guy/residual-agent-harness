#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Mutation:
    name: str
    path: str
    module: str
    anchor: str
    old: str
    new: str
    tests: tuple[str, ...]


MUTATIONS = (
    Mutation(
        "revoked-candidate-acceptance",
        "residual/factory/runtime_journal.py",
        "residual.factory.runtime_journal",
        "    def finish(",
        "if state == 'CANDIDATE' and row[1]:",
        "if state == 'CANDIDATE' and not row[1]:",
        ("tests/qualification/test_trust_boundary_canaries.py::test_revoked_attempt_can_never_publish_candidate",),
    ),
    Mutation(
        "candidate-lease-resurrection",
        "residual/factory/runtime_journal.py",
        "residual.factory.runtime_journal",
        "    def lease_read(",
        "and not row[2] and row[3] in ('RESERVED', 'RUNNING')",
        "and not row[2] and row[3] in ('RESERVED', 'RUNNING', 'CANDIDATE')",
        ("tests/qualification/test_trust_boundary_canaries.py::test_candidate_is_no_longer_an_authoritative_current_lease",),
    ),
    Mutation(
        "git-path-policy-bypass",
        "residual/factory/worker_contract.py",
        "residual.factory.worker_contract",
        "    def permits_path(",
        """if any(part.lower() == ".git" for part in path.split("/")):
            return False""",
        """if any(part.lower() == ".git" for part in path.split("/")):
            return True""",
        ("tests/qualification/test_trust_boundary_canaries.py::test_git_metadata_is_never_permitted_by_worker_path_policy",),
    ),
    Mutation(
        "forbidden-prefix-bypass",
        "residual/factory/worker_contract.py",
        "residual.factory.worker_contract",
        "    def permits_path(",
        """if any(_matches(path, item) for item in self.forbidden):
            return False""",
        """if any(_matches(path, item) for item in self.forbidden):
            return True""",
        ("tests/qualification/test_trust_boundary_canaries.py::test_forbidden_prefix_wins_over_read_allowlist",),
    ),
    Mutation(
        "failed-checks-reach-review",
        "residual/station/service.py",
        "residual.station.service",
        "    def finish(",
        """if not all(c["passed"] for c in checks):""",
        """if False and not all(c["passed"] for c in checks):""",
        ("tests/station/test_station.py::StationTests::test_failed_checks_do_not_reach_review",),
    ),
    Mutation(
        "dependency-dispatch-bypass",
        "residual/station/store.py",
        "residual.station.store",
        "    def claim(",
        """if any(states[d] != "integrated" for d in t["depends_on"]):
                    continue""",
        """if False and any(states[d] != "integrated" for d in t["depends_on"]):
                    continue""",
        ("tests/station/test_station.py::StationTests::test_concurrent_claims_are_exclusive_and_dependencies_wait",),
    ),
    Mutation(
        "pause-dispatch-bypass",
        "residual/station/store.py",
        "residual.station.store",
        "    def claim(",
        """if p["paused"]:
                return None""",
        """if False and p["paused"]:
                return None""",
        ("tests/station/test_station.py::StationTests::test_pause_prevents_claim_and_cloud_disabled_prevents_transport",),
    ),
    Mutation(
        "artifact-integrity-bypass",
        "residual/station/store.py",
        "residual.station.store",
        "    def artifact(",
        """if hashlib.sha256(data).hexdigest() != aid.split(":")[1]:
            raise ContractError("Artifact integrity check failed")""",
        """if False and hashlib.sha256(data).hexdigest() != aid.split(":")[1]:
            raise ContractError("Artifact integrity check failed")""",
        ("tests/station/test_station.py::StationTests::test_artifact_tampering_is_rejected",),
    ),
    Mutation(
        "moving-base-review-bypass",
        "residual/station/service.py",
        "residual.station.service",
        "    def integrate(",
        """if ws.git(p["repo"], "rev-parse", "HEAD") != t["base_commit"]:""",
        """if False and ws.git(p["repo"], "rev-parse", "HEAD") != t["base_commit"]:""",
        ("tests/station/test_station.py::StationTests::test_moving_base_invalidates_review",),
    ),
    Mutation(
        "candidate-review-binding-bypass",
        "residual/station/service.py",
        "residual.station.service",
        "    def integrate(",
        """if ws.git(t["candidate_dir"], "rev-parse", "HEAD") != t["head_commit"] or ws.git(t["candidate_dir"], "status", "--porcelain"):""",
        """if False and (ws.git(t["candidate_dir"], "rev-parse", "HEAD") != t["head_commit"] or ws.git(t["candidate_dir"], "status", "--porcelain")):""",
        ("tests/station/test_station.py::StationTests::test_approval_cannot_survive_changed_candidate",),
    ),
)


def _scope(text: str, mutation: Mutation) -> tuple[int, int, str]:
    start = text.find(mutation.anchor)
    if start < 0:
        return -1, -1, ""
    end = text.find("\n    def ", start + len(mutation.anchor))
    if end < 0:
        end = len(text)
    return start, end, text[start:end]


def mutation_site_count(mutation: Mutation, *, root: Path = ROOT) -> int:
    text = (root / mutation.path).read_text(encoding="utf-8")
    start, _end, scoped = _scope(text, mutation)
    return 0 if start < 0 else scoped.count(mutation.old)


def validate_mutation_sites(*, root: Path = ROOT) -> list[dict[str, object]]:
    invalid = []
    for mutation in MUTATIONS:
        count = mutation_site_count(mutation, root=root)
        if count != 1:
            invalid.append({
                "name": mutation.name,
                "path": mutation.path,
                "anchor": mutation.anchor.strip(),
                "site_count": count,
            })
    return invalid


def _apply_mutation(text: str, mutation: Mutation) -> str:
    start, end, scoped = _scope(text, mutation)
    if start < 0:
        raise ValueError(f"method anchor not found: {mutation.anchor!r}")
    count = scoped.count(mutation.old)
    if count != 1:
        raise ValueError(f"expected one method-scoped mutation site, found {count}")
    return text[:start] + scoped.replace(mutation.old, mutation.new, 1) + text[end:]


def _source_proof(mutation: Mutation, expected_sha256: str, *, env: dict[str, str]) -> dict:
    expected_path = str((ROOT / mutation.path).resolve())
    proof = (
        "import hashlib,importlib,json,pathlib,sys;"
        f"m=importlib.import_module({mutation.module!r});"
        "p=pathlib.Path(m.__file__).resolve();"
        "h=hashlib.sha256(p.read_bytes()).hexdigest();"
        f"ok=(str(p)=={expected_path!r} and h=={expected_sha256!r});"
        "print(json.dumps({'module_file':str(p),'sha256':h,'ok':ok},sort_keys=True));"
        "sys.exit(0 if ok else 23)"
    )
    proc = subprocess.run(
        [sys.executable, "-c", proof],
        cwd=ROOT, capture_output=True, text=True, timeout=30, check=False, env=env,
    )
    try:
        payload = json.loads(proc.stdout.strip().splitlines()[-1]) if proc.stdout.strip() else {}
    except Exception:
        payload = {}
    return {
        "returncode": proc.returncode,
        "stdout": proc.stdout[-2000:],
        "stderr": proc.stderr[-2000:],
        **payload,
    }


def run_mutation(mutation: Mutation) -> dict:
    path = ROOT / mutation.path
    original = path.read_text(encoding="utf-8")
    try:
        mutated = _apply_mutation(original, mutation)
    except ValueError as exc:
        return {"name": mutation.name, "path": mutation.path, "result": "ERROR", "reason": str(exc)}

    mutated_sha256 = hashlib.sha256(mutated.encode("utf-8")).hexdigest()
    try:
        path.write_text(mutated, encoding="utf-8")
        # Same-size mutations can otherwise reuse a just-written timestamp-based .pyc
        # on filesystems with coarse mtime resolution. Each mutant gets a fresh cache.
        with tempfile.TemporaryDirectory(prefix="residual-mutation-pycache-") as pycache:
            env = {**os.environ, "PYTHONPYCACHEPREFIX": pycache}
            proof = _source_proof(mutation, mutated_sha256, env=env)
            if proof.get("returncode") != 0 or proof.get("ok") is not True:
                return {
                    "name": mutation.name,
                    "path": mutation.path,
                    "anchor": mutation.anchor.strip(),
                    "result": "ERROR",
                    "reason": "mutated source identity was not established before test execution",
                    "mutated_sha256": mutated_sha256,
                    "source_proof": proof,
                }
            proc = subprocess.run(
                [sys.executable, "-m", "pytest", "-q", *mutation.tests],
                cwd=ROOT, capture_output=True, text=True, timeout=180, check=False, env=env,
            )
    finally:
        path.write_text(original, encoding="utf-8")

    killed = proc.returncode != 0
    return {
        "name": mutation.name,
        "path": mutation.path,
        "module": mutation.module,
        "anchor": mutation.anchor.strip(),
        "mutated_sha256": mutated_sha256,
        "source_proof": proof,
        "tests": list(mutation.tests),
        "result": "KILLED" if killed else "SURVIVED",
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout[-3000:],
        "stderr_tail": proc.stderr[-3000:],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run deterministic trust-boundary mutation canaries")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    invalid = validate_mutation_sites()
    if invalid:
        report = {
            "schema": "residual.qualification.mutation.v1",
            "mutants": len(MUTATIONS),
            "killed": 0,
            "survived_or_error": len(MUTATIONS),
            "mutation_score": 0.0,
            "result": "FAIL",
            "harness_errors": invalid,
            "results": [],
        }
    else:
        results = [run_mutation(m) for m in MUTATIONS]
        survivors = [r for r in results if r["result"] != "KILLED"]
        report = {
            "schema": "residual.qualification.mutation.v1",
            "mutants": len(results),
            "killed": len(results) - len(survivors),
            "survived_or_error": len(survivors),
            "mutation_score": (len(results) - len(survivors)) / len(results) if results else 0.0,
            "result": "PASS" if not survivors else "FAIL",
            "results": results,
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
